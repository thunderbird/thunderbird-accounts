import datetime
import logging
from typing import Optional

import sentry_sdk
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.dkim import (
    CloudflareDNSClient,
    build_hosted_dkim_txt_record_names,
    build_hosted_dkim_txt_records,
    delete_hosted_dkim_txt_records,
    publish_hosted_dkim_txt_records,
)
from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
    DomainNotFoundError,
    HostedDkimDeleteRetry,
    HostedDkimPublishRetry,
)
from thunderbird_accounts.mail.models import Account, Domain, Email
from thunderbird_accounts.subscription.models import Subscription
from thunderbird_accounts.celery.exceptions import TaskFailed
from thunderbird_accounts.core.types import TaskReturnStatus


def _stalwart_check_or_create_domain_entry(stalwart, domain):
    # Check if we have the domain
    try:
        stalwart.get_domain(domain)
    except DomainNotFoundError:
        # The domain doesn't exist in our records, we'll need to create it first
        # And then the dkim record for the domain
        # Annoyingly they all return null...
        stalwart.create_domain(domain)
        stalwart.create_dkim(domain)


def _base_email_address_to_stalwart_account(fn_name, username, emails):
    """A slightly annoying generic stalwart.*_email_addresses caller.
    They were all the same except for like 1 difference so might as well bundle them up."""
    stalwart = MailClient()

    # Don't create or check domain/dkim entries for deletions
    if 'delete_email_addresses' not in fn_name:
        for email in emails:
            # If it's a replace then we're a tuple, grab the new address
            if 'replace_email_addresses' in fn_name:
                email = email[1]

            # FIXME: Only check this on unique occurrences of domains
            domain = email.split('@')[1]

            # Make sure the domain is in stalwart, otherwise we can't save this address
            _stalwart_check_or_create_domain_entry(stalwart, domain)

    fn = getattr(stalwart, fn_name)
    if not fn:
        logging.error(f'[base_email_address_to_stalwart_account] {fn_name} does not exist!')
        raise TaskFailed(
            f'{fn_name} does not exist',
            {
                'username': username,
                'emails': emails,
            },
        )

    fn(username, emails)

    # Update our main account
    try:
        account = Account.objects.get(name=username)
        now = datetime.datetime.now(datetime.UTC)
        if account.stalwart_updated_at < now:
            account.stalwart_updated_at = now
            account.save()
    except Account.DoesNotExist:
        logging.warning(f'Could not find account with the name {username}, skipping stalwart timestamp updates.')
        pass

    return {
        'username': username,
        'emails': emails,
        'task_status': TaskReturnStatus.SUCCESS,
    }


def _selector_from_hosted_dkim_record_name(record_name: str, domain_name: str) -> str | None:
    hosted_domain = settings.HOSTED_DKIM_DOMAIN
    if not hosted_domain:
        return None

    record_name = record_name.strip().rstrip('.').lower()
    domain_name = domain_name.strip().rstrip('.').lower()
    hosted_domain = hosted_domain.strip().rstrip('.').lower()
    suffix = f'.{domain_name}.{hosted_domain}'
    if not record_name.endswith(suffix):
        return None

    selector = record_name[: -len(suffix)]
    return selector or None


def _validate_configured_stalwart_dkim_selectors(
    domain_name: str,
    stalwart: MailClient,
    *,
    phase: str,
) -> list[str]:
    """ Check if tm1/tm2 selectors are in place """
    expected_selectors = set(settings.STALWART_DKIM_ALGO_SELECTORS.values())
    existing_selectors = stalwart.get_dkim_selectors(domain_name)
    missing_selectors = sorted(expected_selectors - existing_selectors)

    if missing_selectors:
        reason = (
            f'Expected Stalwart DKIM selectors {sorted(expected_selectors)} for {domain_name}, '
            f'but selectors {missing_selectors} are still missing. '
            f'Existing selectors: {sorted(existing_selectors)}'
        )
        logging.error(f'[migrate_legacy_hosted_dkim_domains] {reason}')
        raise HostedDkimPublishRetry(
            domain_name,
            phase,
            reason,
            error_type='HostedDkimSelectorMissing',
        )

    return sorted(existing_selectors)


def _sync_hosted_dkim_dns_records(
    domain_name: str,
    stalwart: MailClient | None = None,
    cloudflare_throttle_seconds: float = 0.0,
) -> dict[str, list | bool]:
    """ Sync DKIM records for a single domain """
    phase = 'initialize'
    dkim_dns_records = []
    hosted_records = []
    expected_selectors = set(settings.STALWART_DKIM_ALGO_SELECTORS.values())

    try:
        phase = 'fetch_stalwart_dkim_dns_records'
        stalwart = stalwart or MailClient()
        dkim_dns_records = stalwart.get_dkim_dns_records(domain_name)

        phase = 'build_hosted_txt_records'
        hosted_records = build_hosted_dkim_txt_records(domain_name, dkim_dns_records)

        phase = 'validate_hosted_txt_records'
        hosted_selectors = {
            selector
            for selector in [
                _selector_from_hosted_dkim_record_name(record.get('name', ''), domain_name) for record in hosted_records
            ]
            if selector
        }
        missing_hosted_selectors = sorted(expected_selectors - hosted_selectors)
        if missing_hosted_selectors:
            dkim_dns_record_names = sorted(record.get('name', '') for record in dkim_dns_records)
            reason = (
                f'Expected hosted DKIM TXT records for selectors {sorted(expected_selectors)} on {domain_name}, '
                f'but selectors {missing_hosted_selectors} are missing. '
                f'Hosted selectors: {sorted(hosted_selectors)}. '
                f'Stalwart DKIM record names: {dkim_dns_record_names}'
            )
            logging.error(f'[sync_hosted_dkim_dns_records] {reason}')
            raise HostedDkimPublishRetry(
                domain_name,
                phase,
                reason,
                error_type='HostedDkimRecordMissing',
            )

        if settings.HOSTED_DKIM_CLOUDFLARE_ENABLED:
            phase = 'publish_cloudflare_txt_records'
            hosted_records = publish_hosted_dkim_txt_records(
                hosted_records,
                dns_client=CloudflareDNSClient(),
                throttle_seconds=cloudflare_throttle_seconds,
            )
            skipped = False
        # Building and logging the full records is still useful for development.
        else:
            for record in hosted_records:
                logging.info(
                    'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS update to set '
                    f'"{record["type"]} {record["name"]} {record["content"]}"'
                )
            skipped = True
    except ImproperlyConfigured:
        raise
    except HostedDkimPublishRetry:
        raise
    except Exception as ex:
        raise HostedDkimPublishRetry(
            domain_name,
            phase,
            str(ex),
            error_type=type(ex).__name__,
        ) from ex

    return {
        'records': hosted_records,
        'skipped': skipped,
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def add_email_addresses_to_stalwart_account(self, username: str, emails: list[str]):
    try:
        return _base_email_address_to_stalwart_account('save_email_addresses', username, emails)
    except RuntimeError as ex:
        logging.error(f'[add_email_addresses_to_stalwart_account] Error adding email address to stalwart account {ex}')
        error = ex
    raise TaskFailed(
        str(error),
        {
            'username': username,
            'emails': emails,
        },
    )


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def replace_email_addresses_on_stalwart_account(self, username: str, emails: list[tuple[str, str]]):
    try:
        return _base_email_address_to_stalwart_account('replace_email_addresses', username, emails)
    except RuntimeError as ex:
        logging.error(
            f'[replace_email_addresses_on_stalwart_account] Error replacing email address to stalwart account {ex}'
        )
        error = ex
    raise TaskFailed(
        str(error),
        {
            'username': username,
            'emails': emails,
        },
    )


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def delete_email_addresses_from_stalwart_account(self, username: str, emails: list[str]):
    try:
        return _base_email_address_to_stalwart_account('delete_email_addresses', username, emails)
    except RuntimeError as ex:
        logging.error(
            f'[delete_email_addresses_from_stalwart_account] Error deleting email address to stalwart account {ex}'
        )
        error = ex
    raise TaskFailed(
        str(error),
        {
            'username': username,
            'emails': emails,
        },
    )


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def update_quota_on_stalwart_account(self, username: str, quota: Optional[int]):
    """Updates the quota value on a stalwart account.
    This will cause the account's storage to be tracked by stalwart."""

    # Small fix for db defaulting to None
    if quota is None:
        quota = 0

    try:
        stalwart = MailClient()
        stalwart.update_quota(username, quota)
    except RuntimeError as ex:
        logging.error(f'[update_quota_on_stalwart_account] Error updating quota on stalwart account {ex}')
        raise TaskFailed(
            str(ex),
            {
                'username': username,
                'quota': quota,
            },
        )
    return {
        'username': username,
        'quota': quota,
        'task_status': TaskReturnStatus.SUCCESS,
    }


@shared_task(
    bind=True,
    autoretry_for=(HostedDkimPublishRetry,),
    retry_backoff=True,
    retry_backoff_max=60 * 60,  # 1 hour
    retry_jitter=True,
    max_retries=24,
)
def publish_hosted_dkim_dns_records(self, domain_name: str):
    phase = 'sync_hosted_dkim_dns_records'
    hosted_records = []
    skipped = False

    try:
        result = _sync_hosted_dkim_dns_records(domain_name)
        hosted_records = result['records']
        skipped = result['skipped']
    except ImproperlyConfigured as ex:
        logging.error(f'[publish_hosted_dkim_dns_records] Hosted DKIM is misconfigured: {ex}')
        raise TaskFailed(str(ex), {'domain': domain_name})
    except HostedDkimPublishRetry as ex:
        sentry_sdk.set_context('hosted_dkim_publish_retry', ex.context)
        logging.warning(f'[publish_hosted_dkim_dns_records] Error publishing hosted DKIM records: {ex}')
        raise
    except Exception as ex:
        retry_error = HostedDkimPublishRetry(
            domain_name,
            phase,
            str(ex),
            error_type=type(ex).__name__,
        )
        sentry_sdk.set_context('hosted_dkim_publish_retry', retry_error.context)
        logging.warning(f'[publish_hosted_dkim_dns_records] Error publishing hosted DKIM records: {retry_error}')
        raise retry_error from ex

    return {
        'domain_name': domain_name,
        'records': hosted_records,
        'skipped': skipped,
        'task_status': TaskReturnStatus.SUCCESS,
    }


def migrate_legacy_hosted_dkim_domains(
    domain_names: list[str] | None = None,
    dry_run: bool = True,
    force_sync: bool = False,
    run_id: str | None = None,
    cloudflare_throttle_seconds: float | None = None,
):
    """Create hosted DKIM selectors for legacy domains that do not have the configured selectors."""
    stalwart = MailClient()
    explicit_domain_names = domain_names is not None
    force_update_explicit_domains = force_sync and explicit_domain_names and not dry_run
    log_context = f' task_id={run_id}' if run_id else ''
    cloudflare_throttle_seconds = (
        settings.HOSTED_DKIM_MIGRATION_CLOUDFLARE_THROTTLE_SECONDS
        if cloudflare_throttle_seconds is None
        else cloudflare_throttle_seconds
    )
    configured_selectors = set(settings.STALWART_DKIM_ALGO_SELECTORS.values())
    all_domain_names = (
        [domain_name.strip().rstrip('.').lower() for domain_name in domain_names]
        if domain_names is not None
        else [
            domain.get('name', '').strip().rstrip('.').lower()
            for domain in stalwart.list_domains()
            if domain.get('name')
        ]
    )
    all_domain_names = sorted({domain_name for domain_name in all_domain_names if domain_name})

    domains_without_tm_selectors = []
    domains_missing_tm_selectors = []
    domains_without_tm_selector_details = []
    domains_missing_tm_selector_details = []
    updated_domains = []

    for domain_name in all_domain_names:
        existing_selectors = stalwart.get_dkim_selectors(domain_name)
        missing_selectors = sorted(configured_selectors - existing_selectors)

        domain = Domain.objects.select_related('user').filter(name__iexact=domain_name).first()
        if domain:
            user = domain.user
            owner_email = user.recovery_email or user.email or user.username
            subscription_statuses = sorted(user.subscription_set.values_list('status', flat=True))
            active_customer = str(Subscription.StatusValues.ACTIVE.value in subscription_statuses).lower()
        else:
            owner_email = 'unknown'
            active_customer = 'unknown'
            subscription_statuses = []

        owner_context = (
            f'owner_email={owner_email} '
            f'active_customer={active_customer} '
            f'subscription_statuses={subscription_statuses}'
        )
        domain_context = {
            'domain_name': domain_name,
            'owner_email': owner_email,
            'active_customer': active_customer,
            'subscription_statuses': subscription_statuses,
            'existing_selectors': sorted(existing_selectors),
            'missing_selectors': missing_selectors,
        }

        if not missing_selectors:
            logging.info(
                '[migrate_legacy_hosted_dkim_domains] domain already has configured DKIM selectors: '
                f'{domain_name} existing_selectors={sorted(existing_selectors)} {owner_context}{log_context}'
            )
            if not force_update_explicit_domains:
                continue

        if not missing_selectors:
            logging.info(
                '[migrate_legacy_hosted_dkim_domains] '
                f'explicit domain will be re-synced even though configured DKIM selectors exist: {domain_name} '
                f'{owner_context}{log_context}'
            )
        elif configured_selectors.isdisjoint(existing_selectors):
            logging.info(
                '[migrate_legacy_hosted_dkim_domains] '
                f'found domain without any `tm` selectors: {domain_name} {owner_context}{log_context}'
            )
            domains_without_tm_selectors.append(domain_name)
            domains_without_tm_selector_details.append(domain_context)
        else:
            logging.info(
                '[migrate_legacy_hosted_dkim_domains] '
                f'found domain missing configured `tm` selectors: {domain_name} '
                f'missing_selectors={missing_selectors} existing_selectors={sorted(existing_selectors)} '
                f'{owner_context}{log_context}'
            )
            domains_missing_tm_selectors.append(domain_name)
            domains_missing_tm_selector_details.append(domain_context)

    domains_to_update = (
        all_domain_names
        if force_update_explicit_domains
        else domains_without_tm_selectors + domains_missing_tm_selectors
    )

    if dry_run:
        logging.info(
            '[migrate_legacy_hosted_dkim_domains] dry_run=true: '
            f'skipping hosted DKIM migration for {len(domains_to_update)} domain(s){log_context}'
        )
        return {
            'dry_run': True,
            'domains_without_tm_selectors': domains_without_tm_selectors,
            'domains_missing_tm_selectors': domains_missing_tm_selectors,
            'domains_without_tm_selector_details': domains_without_tm_selector_details,
            'domains_missing_tm_selector_details': domains_missing_tm_selector_details,
            'updated_domains': updated_domains,
            'task_status': TaskReturnStatus.SUCCESS,
        }

    for domain_name in domains_to_update:
        try:
            logging.info(
                f'[migrate_legacy_hosted_dkim_domains] updating hosted DKIM records for {domain_name}{log_context}'
            )
            created_signatures = stalwart.ensure_dkim(domain_name)
            post_create_selectors = _validate_configured_stalwart_dkim_selectors(
                domain_name,
                stalwart,
                phase='validate_stalwart_dkim_selectors',
            )
            sync_result = _sync_hosted_dkim_dns_records(
                domain_name,
                stalwart=stalwart,
                cloudflare_throttle_seconds=cloudflare_throttle_seconds,
            )
            logging.info(
                f'[migrate_legacy_hosted_dkim_domains] updated hosted DKIM records for {domain_name}{log_context}'
            )
        except ImproperlyConfigured as ex:
            logging.error(f'[migrate_legacy_hosted_dkim_domains] Hosted DKIM is misconfigured: {ex}')
            raise TaskFailed(str(ex), {'domain': domain_name})
        except HostedDkimPublishRetry as ex:
            sentry_sdk.set_context('hosted_dkim_migration_retry', ex.context)
            logging.warning(f'[migrate_legacy_hosted_dkim_domains] Error migrating hosted DKIM records: {ex}')
            raise

        updated_domains.append(
            {
                'domain_name': domain_name,
                'created_signatures': created_signatures,
                'post_create_selectors': post_create_selectors,
                'records': sync_result['records'],
                'skipped': sync_result['skipped'],
            }
        )

    result = {
        'dry_run': False,
        'domains_without_tm_selectors': domains_without_tm_selectors,
        'domains_missing_tm_selectors': domains_missing_tm_selectors,
        'domains_without_tm_selector_details': domains_without_tm_selector_details,
        'domains_missing_tm_selector_details': domains_missing_tm_selector_details,
        'updated_domains': updated_domains,
        'task_status': TaskReturnStatus.SUCCESS,
    }
    logging.info(
        '[migrate_legacy_hosted_dkim_domains] completed hosted DKIM migration '
        f'domains_to_update={len(domains_to_update)} updated_domains={len(updated_domains)}{log_context}'
    )
    return result


@shared_task(
    bind=True,
    autoretry_for=(HostedDkimPublishRetry,),
    retry_backoff=True,
    retry_backoff_max=60 * 60,  # 1 hour
    retry_jitter=True,
    max_retries=24,
)
def migrate_legacy_hosted_dkim_domains_task(
    self,
    domain_names: list[str] | None = None,
    dry_run: bool = False,
    force_sync: bool = False,
):
    logging.info(
        '[migrate_legacy_hosted_dkim_domains_task] starting hosted DKIM migration '
        f'task_id={self.request.id} dry_run={str(dry_run).lower()}'
    )
    result = migrate_legacy_hosted_dkim_domains(
        domain_names=domain_names,
        dry_run=dry_run,
        force_sync=force_sync,
        run_id=self.request.id,
    )
    logging.info(
        '[migrate_legacy_hosted_dkim_domains_task] completed hosted DKIM migration '
        f'task_id={self.request.id} task_status={result.get("task_status")} '
        f'updated_domains={len(result.get("updated_domains", []))}'
    )
    return result


@shared_task(
    bind=True,
    autoretry_for=(HostedDkimDeleteRetry,),
    retry_backoff=True,
    retry_backoff_max=60 * 60,  # 1 hour
    retry_jitter=True,
    max_retries=24,
)
def delete_hosted_dkim_dns_records(self, domain_name: str):
    phase = 'initialize'
    hosted_records = []

    try:
        phase = 'build_hosted_txt_record_names'
        hosted_records = [{'type': 'TXT', 'name': name} for name in build_hosted_dkim_txt_record_names(domain_name)]

        if settings.HOSTED_DKIM_CLOUDFLARE_ENABLED:
            phase = 'delete_cloudflare_txt_records'
            hosted_records = delete_hosted_dkim_txt_records(
                domain_name,
                dns_client=CloudflareDNSClient(),
            )
            skipped = False
        else:
            for record in hosted_records:
                logging.info(
                    '[delete_hosted_dkim_dns_records] '
                    'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS delete for '
                    f'"{record["type"]} {record["name"]}"'
                )
            skipped = True
    except ImproperlyConfigured as ex:
        logging.error(f'[delete_hosted_dkim_dns_records] Hosted DKIM is misconfigured: {ex}')
        raise TaskFailed(str(ex), {'domain': domain_name})
    except HostedDkimDeleteRetry as ex:
        sentry_sdk.set_context('hosted_dkim_delete_retry', ex.context)
        logging.warning(f'[delete_hosted_dkim_dns_records] Error deleting hosted DKIM records: {ex}')
        raise
    except Exception as ex:
        retry_error = HostedDkimDeleteRetry(
            domain_name,
            phase,
            str(ex),
            error_type=type(ex).__name__,
        )
        sentry_sdk.set_context('hosted_dkim_delete_retry', retry_error.context)
        logging.warning(f'[delete_hosted_dkim_dns_records] Error deleting hosted DKIM records: {retry_error}')
        raise retry_error from ex

    return {
        'domain_name': domain_name,
        'records': hosted_records,
        'skipped': skipped,
        'task_status': TaskReturnStatus.SUCCESS,
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def create_stalwart_account(
    self,
    oidc_id: str,
    username: str,
    email: str,
    full_name: Optional[str] = None,
    app_password: Optional[str] = None,
    quota: Optional[int] = None,
):
    from thunderbird_accounts.subscription.tasks import add_subscriber_to_mailchimp_list

    """Creates a Stalwart Account with the given parameters. OIDC ID is currently just used for error logging,
    but is still required. App Passwords can be set now, or later.

    Note: Email should be Thundermail address. Stalwart does not need your recovery email."""
    stalwart = MailClient()
    domain = email.split('@')[1]

    if domain != settings.PRIMARY_EMAIL_DOMAIN:
        error = f'Cannot create Stalwart account with non-primary email domain: {domain}'
        logging.error(f'[create_stalwart_account] {error}')

        raise TaskFailed(
            str(error),
            {
                'oidc_id': oidc_id,
                'username': username,
                'email': email,
            },
        )

    emails = [
        email,
        # Create every other allowed alias too
        *[
            email.replace(f'@{settings.PRIMARY_EMAIL_DOMAIN}', f'@{_domain}')
            for _domain in settings.ALLOWED_EMAIL_DOMAINS[1:]
        ],
    ]

    _stalwart_check_or_create_domain_entry(stalwart, domain)
    for alias in emails[1:]:
        _domain = alias.split('@')[1]
        _stalwart_check_or_create_domain_entry(stalwart, _domain)

    # Lookup the account first, this shouldn't normally happen but if it does we shouldn't explode.
    try:
        stalwart_account = stalwart.get_account(username)
        stalwart_emails = stalwart_account.get('emails', [])

        # link the stalwart account
        pkid = stalwart_account.get('id')

        # Check the aliases
        if emails != stalwart_emails:
            # Diff of new emails
            new_emails = set(emails) - set(stalwart_emails)
            # Diff of the old emails
            old_emails = set(stalwart_emails) - set(emails)

            stalwart.save_email_addresses(username, list(new_emails))
            stalwart.delete_email_addresses(username, list(old_emails))
    except AccountNotFoundError:
        # We need to create this after dkim and domain records exist
        pkid = stalwart.create_account(emails, username, full_name, app_password, quota)

    user = User.objects.get(oidc_id=oidc_id)
    now = datetime.datetime.now(datetime.UTC)

    # Don't create the account if we already have it
    # Also create their account objects
    account, _created = Account.objects.update_or_create(
        name=user.username,
        defaults={
            'active': True,
            'quota': quota,
            'stalwart_id': pkid,
            'stalwart_updated_at': now,
        },
        create_defaults={
            'active': True,
            'quota': quota,
            'stalwart_id': pkid,
            'stalwart_updated_at': now,
            'user_id': user.uuid,
            'stalwart_created_at': now,
        },
    )

    # Edge-case: don't override an existing stalwart_created_at timestamp
    if not account.stalwart_created_at:
        account.stalwart_created_at = now
        account.save()

    Email.objects.update_or_create(
        address=user.username,
        create_defaults={
            'type': Email.EmailType.PRIMARY.value,
            'account_id': account.uuid,
        },
    )
    for alias in emails[1:]:
        Email.objects.update_or_create(
            address=alias,
            create_defaults={
                'type': Email.EmailType.ALIAS.value,
                'account_id': account.uuid,
            },
        )

    # Fire off the task to add folks to the mailing list (so we can send them a welcome email)
    if settings.USE_MAILCHIMP:
        add_subscriber_to_mailchimp_list.delay(str(user.uuid))

    return {
        'oidc_id': oidc_id,
        'stalwart_pkid': pkid,
        'username': username,
        'email': email,
        'task_status': TaskReturnStatus.SUCCESS,
    }
