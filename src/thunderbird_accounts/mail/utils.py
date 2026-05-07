from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from thunderbird_accounts.mail.exceptions import EmailNotValidError
import logging
import uuid
from typing import Optional
from requests.exceptions import HTTPError
from django.contrib.auth.hashers import make_password, identify_hasher
from django.utils.translation import gettext_lazy as _
import sentry_sdk

from django.conf import settings
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account
from thunderbird_accounts.mail import tasks


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
                            'accountId': account_id,
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
            inbox_res = client.make_jmap_call(
                {
                    'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
                    'methodCalls': [
                        [
                            'Mailbox/set',
                            {
                                'accountId': account_id,
                                'create': {
                                    temp_id: {
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

            method_response = inbox_res['methodResponses'][0][1]
            return_response = method_response.get('created')
            if not return_response:
                return_response = method_response.get('notCreated', {})
                # The only way we're getting out of here without an error, is if the folder already exists
                desc = return_response.get(temp_id, {}).get('description')
                if desc and desc in already_exists_descriptions:
                    raise Exception(f'Failed to create archive folder: {desc}')
            elif temp_id not in return_response:
                # Note: If the request didn't work, it won't have temp_id in it,
                # or if it's malformed it'll raise a keyerror.
                raise Exception('Failed to create archive folder')

        # If we got here without an error, then we can mark this as verified
        account.verified_archive_folder = True
        account.save()

        return True
    except (HTTPError, Exception, KeyError) as ex:
        logging.error('fix_archive_folder failed!')
        sentry_sdk.set_extra('inbox_response', inboxes)
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
