import dns.rdatatype
import dns.resolver
import logging
import uuid
import sentry_sdk
from typing import Optional
from requests.exceptions import HTTPError
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import make_password, identify_hasher
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from thunderbird_accounts.mail.exceptions import EmailNotValidError
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.mail.clients import DNSRecordStatus, StaleDNSRecordCode
from thunderbird_accounts.mail import tasks


def normalize_dns_query_name(name: str, domain_name: str) -> str:
    if name == '@':
        return f'{domain_name.rstrip(".")}.'
    return name if name.endswith('.') else f'{name}.'


def txt_tag_value(content: str, tag: str) -> Optional[str]:
    for part in content.split(';'):
        part = part.strip()
        if part.startswith(f'{tag}='):
            return part[len(tag) + 1 :]
    return None


def normalize_txt_content(content: str) -> str:
    return ' '.join(content.split())


def check_mx_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    expected_host = record['content'].rstrip('.').lower()
    expected_priority = int(record.get('priority', '10'))

    try:
        answers = dns.resolver.resolve(query_name, 'MX')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        logging.debug(f'MX lookup failed for {query_name} resulted in NXDOMAIN')
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'MX lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = []
    has_match = False
    same_priority_conflicts = []

    for rdata in answers:
        exchange = rdata.exchange.to_text().rstrip('.')
        preference = rdata.preference
        live_value = f'{preference} {exchange}'
        live_values.append(live_value)
        if exchange.lower() == expected_host and preference == expected_priority:
            has_match = True
        elif preference == expected_priority:
            same_priority_conflicts.append(live_value)

    if has_match:
        if same_priority_conflicts:
            logging.debug(
                f'MX lookup for {query_name} resulted in same-priority conflict with {same_priority_conflicts}'
            )
            return DNSRecordStatus.CONFLICT, same_priority_conflicts
        return DNSRecordStatus.MATCH, []
    if live_values:
        logging.debug(f'MX lookup for {query_name} resulted in conflict with {live_values}')
        return DNSRecordStatus.CONFLICT, live_values
    return DNSRecordStatus.MISSING, []


def check_srv_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    content_parts = record['content'].split()
    expected_weight = int(content_parts[0])
    expected_port = int(content_parts[1])
    expected_target = content_parts[2].rstrip('.').lower()
    expected_priority = int(record.get('priority', '0'))

    try:
        answers = dns.resolver.resolve(query_name, 'SRV')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'SRV lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = []
    has_match = False

    for rdata in answers:
        target = rdata.target.to_text().rstrip('.')
        live_value = f'{rdata.priority} {rdata.weight} {rdata.port} {target}'
        live_values.append(live_value)
        if (
            rdata.priority == expected_priority
            and rdata.weight == expected_weight
            and rdata.port == expected_port
            and target.lower() == expected_target
        ):
            has_match = True

    if has_match:
        return DNSRecordStatus.MATCH, []
    if live_values:
        return DNSRecordStatus.CONFLICT, live_values
    return DNSRecordStatus.MISSING, []


def check_cname_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    expected_target = record['content'].rstrip('.').lower()

    try:
        answers = dns.resolver.resolve(query_name, 'CNAME')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'CNAME lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = [rdata.target.to_text().rstrip('.') for rdata in answers]

    if any(value.lower() == expected_target for value in live_values):
        return DNSRecordStatus.MATCH, []
    if live_values:
        return DNSRecordStatus.CONFLICT, live_values
    return DNSRecordStatus.MISSING, []


def _compare_dkim_txt(expected_content: str, live_values: list[str]) -> tuple[DNSRecordStatus, list[str]]:
    expected_p = txt_tag_value(expected_content, 'p')
    dkim_values = [value for value in live_values if 'v=DKIM1' in value]

    if not dkim_values:
        return DNSRecordStatus.MISSING, []

    if expected_p and any(txt_tag_value(value, 'p') == expected_p for value in dkim_values):
        return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, dkim_values


def _compare_spf_txt(expected_content: str, live_values: list[str]) -> tuple[DNSRecordStatus, list[str]]:
    spf_values = [value for value in live_values if value.startswith('v=spf1')]

    if not spf_values:
        return DNSRecordStatus.MISSING, []

    expected_include = next(
        (part.strip() for part in expected_content.split() if part.strip().startswith('include:')),
        None,
    )

    for value in spf_values:
        if expected_include and expected_include in value.split():
            if len(spf_values) == 1:
                return DNSRecordStatus.MATCH, []
            conflicting = [candidate for candidate in spf_values if expected_include not in candidate.split()]
            if conflicting:
                return DNSRecordStatus.CONFLICT, spf_values
            return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, spf_values


def _compare_semantic_txt(
    expected_content: str, live_values: list[str], *, prefix: str
) -> tuple[DNSRecordStatus, list[str]]:
    relevant_values = [value for value in live_values if value.startswith(prefix)]

    if not relevant_values:
        return DNSRecordStatus.MISSING, []

    normalized_expected = normalize_txt_content(expected_content)
    if any(normalize_txt_content(value) == normalized_expected for value in relevant_values):
        return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, relevant_values


def check_txt_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    expected_content = record['content']

    try:
        answers = dns.resolver.resolve(query_name, 'TXT')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'TXT lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = [b''.join(rdata.strings).decode('utf-8') for rdata in answers]

    if '_domainkey' in query_name:
        return _compare_dkim_txt(expected_content, live_values)
    if expected_content.startswith('v=spf1'):
        return _compare_spf_txt(expected_content, live_values)
    if query_name.startswith('_dmarc.'):
        return _compare_semantic_txt(expected_content, live_values, prefix='v=DMARC1')
    if query_name.startswith('_mta-sts.'):
        return _compare_semantic_txt(expected_content, live_values, prefix='v=STSv1')
    if query_name.startswith('_smtp._tls.'):
        return _compare_semantic_txt(expected_content, live_values, prefix='v=TLSRPTv1')

    return DNSRecordStatus.UNKNOWN, []


def check_dns_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    """Check customer domain_name against record with expected values"""
    record_type = record.get('type', '').upper()
    if record_type == 'MX':
        return check_mx_record_status(domain_name, record)
    if record_type == 'SRV':
        return check_srv_record_status(domain_name, record)
    if record_type == 'CNAME':
        return check_cname_record_status(domain_name, record)
    if record_type == 'TXT':
        return check_txt_record_status(domain_name, record)
    return DNSRecordStatus.UNKNOWN, []


def enrich_dns_records_with_status(domain_name: str, expected_records: list[dict]) -> list[dict]:
    enriched_records = []
    for record in expected_records:
        status, existing_values = check_dns_record_status(domain_name, record)
        enriched = {**record, 'status': status.value}
        if existing_values:
            enriched['existing_values'] = existing_values
        enriched_records.append(enriched)
    logging.debug('Returning DNS records with status: %s', enriched_records)
    return enriched_records


def _stale_dns_resolve(resolver: dns.resolver.Resolver, name: str, rdtype: str):
    """Thin wrapper so callers don't repeat the exception tuple."""
    return resolver.resolve(name, rdtype)


def _unique_dns_values(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _cname_targets_from_rdata(records) -> list[str]:
    return _unique_dns_values([rdata.target.to_text().rstrip('.') for rdata in records])


def _cname_targets_from_response(answer) -> list[str]:
    targets = []
    for rrset in getattr(getattr(answer, 'response', None), 'answer', []):
        if rrset.rdtype == dns.rdatatype.CNAME:
            targets.extend(rdata.target.to_text().rstrip('.') for rdata in rrset)
    return _unique_dns_values(targets)


def _resolve_autodiscover_cname_targets(resolver: dns.resolver.Resolver, name: str) -> list[str]:
    """Return CNAME targets, including chains visible only through address lookups."""
    targets = []
    try:
        targets.extend(_cname_targets_from_rdata(_stale_dns_resolve(resolver, name, 'CNAME')))
        if targets:
            return _unique_dns_values(targets)
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        pass
    except dns.resolver.NXDOMAIN:
        return []
    except Exception as e:
        logging.warning(f'CNAME lookup failed for {name}: {e}')

    for rdtype in ('A', 'AAAA'):
        try:
            answer = _stale_dns_resolve(resolver, name, rdtype)
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            continue
        except dns.resolver.NXDOMAIN:
            return _unique_dns_values(targets)
        except Exception as e:
            logging.warning(f'{rdtype} lookup failed for {name}: {e}')
            continue

        targets.extend(_cname_targets_from_response(answer))

    return _unique_dns_values(targets)


def _resolve_autodiscover_address_records(resolver: dns.resolver.Resolver, name: str) -> dict[str, list[str]]:
    """Return direct A/AAAA records for autodiscover, excluding CNAME target addresses."""
    address_records = {}
    for rdtype in ('A', 'AAAA'):
        try:
            answers = _stale_dns_resolve(resolver, name, rdtype)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            continue
        except Exception as e:
            logging.warning(f'{rdtype} lookup failed for {name}: {e}')
            continue

        if _cname_targets_from_response(answers):
            continue

        live_values = [rdata.to_text() for rdata in answers]
        if live_values:
            address_records[rdtype] = _unique_dns_values(live_values)

    return address_records


def check_stale_dns_records(cust_domain: str) -> list[dict]:
    """Detect DNS records that exist but should be deleted."""
    stale_records = []

    resolver = dns.resolver.Resolver()
    resolver.lifetime = settings.STALE_DNS_LOOKUP_LIFETIME

    # We currently don't show autodiscover records during custom domain setup
    # so if they have it we should mark as stale / ask for removing it
    # as it can trigger Office 365 / Exchange in Thunderbird Desktop
    autodiscover_name = f'autodiscover.{cust_domain}'
    cname_targets = _resolve_autodiscover_cname_targets(resolver, autodiscover_name)
    if cname_targets:
        stale_records.append(
            {
                'code': StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value,
                'type': 'CNAME',
                'name': autodiscover_name,
                'existing_values': cname_targets,
            }
        )
    else:
        for record_type, address_records in _resolve_autodiscover_address_records(resolver, autodiscover_name).items():
            stale_records.append(
                {
                    'code': StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value,
                    'type': record_type,
                    'name': autodiscover_name,
                    'existing_values': address_records,
                }
            )

    autodiscover_srv_name = f'_autodiscover._tcp.{cust_domain}'
    try:
        answers = _stale_dns_resolve(resolver, autodiscover_srv_name, 'SRV')
        live_values = [
            f'{rdata.priority} {rdata.weight} {rdata.port} {rdata.target.to_text().rstrip(".")}'
            for rdata in answers
        ]
        if live_values:
            stale_records.append(
                {
                    'code': StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value,
                    'type': 'SRV',
                    'name': autodiscover_srv_name,
                    'existing_values': live_values,
                }
            )
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        pass
    except Exception as e:
        logging.warning(f'SRV lookup failed for {autodiscover_srv_name}: {e}')

    logging.debug("stale DNS records that should be deleted %s", stale_records)
    return stale_records


def validate_email(email: str, error_message: str | None = None, min_length: int | None = None) -> bool:
    """Validates the email and local part against Django's built-in email validation.

    min_length overrides User.USERNAME_MIN_LENGTH when the caller has already
    enforced its own domain-specific minimum (e.g. the add_email_alias view).
    """
    not_valid_err_msg = error_message or _('This email is not valid. Try another one.')

    if '@' not in email:
        raise EmailNotValidError(email, not_valid_err_msg)

    local_part = email.split('@')[0]
    effective_min = min_length if min_length is not None else User.USERNAME_MIN_LENGTH

    # EmailValidator allows for up to 350 characters, but username is defined with max_length of 150.
    # We also need to validate the minimum length of the username.
    if len(local_part) > User.USERNAME_MAX_LENGTH or len(local_part) < effective_min:
        raise EmailNotValidError(email, not_valid_err_msg)

    email_validator = EmailValidator(not_valid_err_msg)
    # So EmailValidator.__call__ will raise a ValidationError if it fails, but they're the wrong
    # ValidationError...So catch this ValidationError so we can raise DRF's ValidationError.
    try:
        email_validator(email)
    except ValidationError as ex:
        raise EmailNotValidError(email, ex.message)

    return True


def save_app_password(label, password):
    """Hashes a given password, formats it with the label and saves it to the secret field."""
    hashed_password = make_password(password, hasher='argon2')
    hash_algo = identify_hasher(hashed_password)

    # We need to strip out the leading argon2$ from the hashed value
    if hash_algo.algorithm == 'argon2':
        _, hashed_password = hashed_password.split('argon2$')
        # Note: This is an intentional $, not a failed javascript template literal
        hashed_password = f'${hashed_password}'
    else:
        return None

    secret_string = f'$app${label}${hashed_password}'
    return secret_string


def filter_app_passwords(secrets: list[str], *, filter_prefix: str | None = None) -> list[str]:
    """Return app-password secrets with Appointment CalDAV entry excluded.

    If filter_prefix is given, only secrets whose label starts with that
    prefix are kept (all others are returned).  By default the
    ``APPOINTMENT_APP_PASSWORD_PREFIX`` is stripped out.
    """
    prefix = f'$app${filter_prefix or settings.APPOINTMENT_APP_PASSWORD_PREFIX}'
    return [s for s in secrets if not s.startswith(prefix)]


def decode_app_password(secret):
    if not secret:
        return ''

    # We only care about the app password name here
    return secret.replace('$app$', '').split('$')[0]


def create_stalwart_account(user, app_password: Optional[str] = None) -> bool:
    if user.account_set.count() > 0 and user.account_set.first().stalwart_id:
        return False

    mail_quota = None
    if user.plan_id:
        mail_quota = user.plan.mail_storage_bytes

    tasks.create_stalwart_account.delay(
        oidc_id=user.oidc_id, username=user.username, email=user.username, app_password=app_password, quota=mail_quota
    )

    return True


def fix_archives_folder(access_token, account: Account) -> bool:
    """Check if the archive folder exists, if it doesn't create it!
    This fixes a bug with our stalwart instance where it doesn't give us an archives folder...

    This function is a little messy, and will hopefully be removed in the future."""
    from thunderbird_accounts.mail.tiny_jmap_client import TinyJMAPClient

    if not access_token:
        return False

    inboxes = None

    try:
        client = TinyJMAPClient(
            hostname=settings.STALWART_BASE_JMAP_URL,
            username=account.name,
            token=access_token,
        )
        account_id = client.get_account_id()

        # Look up if they have an archives folder
        inbox_res = client.make_jmap_call(
            {
                'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
                'methodCalls': [
                    [
                        'Mailbox/query',
                        {
                            'accountId': str(account_id),
                            'filter': {'role': 'archive'},
                        },
                        '0',
                    ]
                ],
            }
        )

        inboxes = inbox_res['methodResponses'][0][1]['ids']
        if len(inboxes) == 0:
            # If they don't create a new inbox with the role 'archive', named 'Archives'
            # (set in settings.STALWART_ARCHIVES_FOLDER_NAME) which is subscribed by default
            temp_id = str(uuid.uuid4())
            set_res = client.make_jmap_call(
                {
                    'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
                    'methodCalls': [
                        [
                            'Mailbox/set',
                            {
                                'accountId': str(account_id),
                                'create': {
                                    str(temp_id): {
                                        'name': settings.STALWART_ARCHIVES_FOLDER_NAME,
                                        'role': 'archive',
                                        'isSubscribed': True,
                                    }
                                },
                            },
                            '0',
                        ]
                    ],
                }
            )

            """
            Response looks like this:
            {
                'methodResponses': [
                    [
                        'Mailbox/set',
                        {
                            'accountId': 'e', 
                            'oldState': 'sae', 
                            'newState': 'sai', 
                            'created': {
                                '464ff50a-0e53-45f4-a5af-a0f77d0fb232': { # <--- temp_id
                                    'id': 'h'
                                }
                            }
                        }, 
                        '0'
                    ]
                ], 'sessionState': '3e25b2a0'
            }
            """

            # Either a mailbox named Archives or with the role archive will do
            already_exists_descriptions = [
                f"A mailbox with name '{settings.STALWART_ARCHIVES_FOLDER_NAME}' already exists.",
                "A mailbox with role 'archive' already exists.",
            ]

            method_response = set_res['methodResponses'][0][1]
            return_response = method_response.get('created')
            if not return_response:
                return_response = method_response.get('notCreated', {})
                # The only way we're getting out of here without an error, is if the folder already exists
                desc = return_response.get(temp_id, {}).get('description')
                
                if desc and desc in already_exists_descriptions:
                    pass # If it already exists then we can actually mark it as done and move on
                else:
                    sentry_sdk.set_context('desc', {'desc': desc})
                    raise RuntimeError('Failed to create archive folder')
            elif temp_id not in return_response:
                # Note: If the request didn't work, it won't have temp_id in it,
                # or if it's malformed it'll raise a keyerror.
                raise RuntimeError('Failed to create archive folder')

        # If we got here without an error, then we can mark this as verified
        account.verified_archive_folder = True
        account.save()

        return True
    except (HTTPError, RuntimeError, KeyError) as ex:
        logging.error('fix_archive_folder failed!')
        sentry_sdk.set_context('inbox_response', {'inbox':inboxes})
        sentry_sdk.capture_exception(ex)

    return False


def add_email_addresses_to_stalwart_account(user: User, emails):
    tasks.add_email_addresses_to_stalwart_account.delay(username=user.username, emails=emails)


def replace_email_addresses_on_stalwart_account(user: User, emails):
    tasks.replace_email_addresses_on_stalwart_account.delay(username=user.username, emails=emails)


def delete_email_addresses_from_stalwart_account(user: User, emails):
    tasks.delete_email_addresses_from_stalwart_account.delay(username=user.username, emails=emails)


def is_allowed_domain(email_address: str) -> bool:
    """Pass in an email address and see if it's a valid / allowed email domain"""
    return any([email_address.endswith(f'@{domain}') for domain in settings.ALLOWED_EMAIL_DOMAINS])


def is_address_taken(email_address: str) -> bool:
    """Checks an email address (thundermail address or custom alias, not recovery email!) against known
    user's recovery email, thundermail address or custom aliases."""
    from thunderbird_accounts.authentication.models import User
    from thunderbird_accounts.mail.models import Email
    from django.db.models import Q

    # Make sure a user does not exist with their email address
    user = User.objects.filter(Q(email=email_address) | Q(username=email_address)).exists()
    if user:
        return True

    # Make sure there's no email alias with this address
    aliases = Email.objects.filter(address=email_address).exists()
    if aliases:
        return True

    return False


def update_quota_on_stalwart_account(user: User, quota: Optional[int]):
    tasks.update_quota_on_stalwart_account.delay(username=user.username, quota=quota)
