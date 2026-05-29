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
    build_hosted_dkim_txt_records,
    publish_hosted_dkim_txt_records,
)
from thunderbird_accounts.mail.exceptions import AccountNotFoundError, DomainNotFoundError, HostedDkimPublishRetry
from thunderbird_accounts.mail.models import Account, Email
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
    phase = 'initialize'
    dkim_dns_records = []
    hosted_records = []
    expected_record_count = len(
        {selector for selector in settings.STALWART_DKIM_ALGO_SELECTORS.values() if selector}
    )

    try:
        phase = 'fetch_stalwart_dkim_dns_records'
        stalwart = MailClient()
        dkim_dns_records = stalwart.get_dkim_dns_records(domain_name)

        if settings.HOSTED_DKIM_CLOUDFLARE_ENABLED:
            phase = 'publish_cloudflare_txt_records'
            hosted_records = publish_hosted_dkim_txt_records(
                domain_name,
                dkim_dns_records,
                dns_client=CloudflareDNSClient(),
            )
            phase = 'validate_hosted_record_count'
            if len(hosted_records) < expected_record_count:
                reason = (
                    f'Expected {expected_record_count} hosted DKIM records for {domain_name}, '
                    f'got {len(hosted_records)}'
                )
                raise HostedDkimPublishRetry(
                    domain_name,
                    phase,
                    reason,
                    error_type='HostedDkimRecordCountMismatch',
                )
            skipped = False
        # Building and logging the full records is still useful for development.
        else:
            phase = 'build_hosted_txt_records'
            hosted_records = build_hosted_dkim_txt_records(domain_name, dkim_dns_records)
            for record in hosted_records:
                logging.info(
                    'HOSTED_DKIM_CLOUDFLARE_ENABLED=false: skipping DNS update to set '
                    f'"{record["type"]} {record["name"]} {record["content"]}"'
                )
            skipped = True
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
