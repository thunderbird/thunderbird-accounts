import datetime
import logging
from typing import Optional

import sentry_sdk
from celery import shared_task
from django.conf import settings

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError
from thunderbird_accounts.mail.models import Account, Email


def _stalwart_check_or_create_domain_entry(stalwart, domain):
    # Check if we have the domain
    try:
        domain = stalwart.get_domain(domain)
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
        return {
            'username': username,
            'emails': emails,
            'reason': f'{fn_name} does not exist',
            'task_status': 'failed',
        }

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
        'task_status': 'success',
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def add_email_addresses_to_stalwart_account(self, username: str, emails: list[str]):
    try:
        return _base_email_address_to_stalwart_account('save_email_addresses', username, emails)
    except RuntimeError as ex:
        logging.error(f'[add_email_addresses_to_stalwart_account] Error adding email address to stalwart account {ex}')
        error = ex
    return {
        'username': username,
        'emails': emails,
        'reason': error,
        'task_status': 'failed',
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def replace_email_addresses_on_stalwart_account(self, username: str, emails: list[tuple[str, str]]):
    try:
        return _base_email_address_to_stalwart_account('replace_email_addresses', username, emails)
    except RuntimeError as ex:
        logging.error(
            f'[replace_email_addresses_on_stalwart_account] Error replacing email address to stalwart account {ex}'
        )
        error = ex
    return {
        'username': username,
        'emails': emails,
        'reason': error,
        'task_status': 'failed',
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def delete_email_addresses_from_stalwart_account(self, username: str, emails: list[str]):
    try:
        return _base_email_address_to_stalwart_account('delete_email_addresses', username, emails)
    except RuntimeError as ex:
        logging.error(
            f'[delete_email_addresses_from_stalwart_account] Error deleting email address to stalwart account {ex}'
        )
        error = ex
    return {
        'username': username,
        'emails': emails,
        'reason': error,
        'task_status': 'failed',
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def update_quota_on_stalwart_account(self, username: str, quota: int):
    """Updates the quota value on a stalwart account.
    This will cause the account's storage to be tracked by stalwart."""
    try:
        stalwart = MailClient()
        stalwart.update_quota(username, quota)
    except RuntimeError as ex:
        logging.error(f'[update_quota_on_stalwart_account] Error updating quota on stalwart account {ex}')
        return {
            'username': username,
            'quota': quota,
            'reason': ex,
            'task_status': 'failed',
        }
    return {
        'username': username,
        'quota': quota,
        'task_status': 'success',
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
    """Creates a Stalwart Account with the given parameters. OIDC ID is currently just used for error logging,
    but is still required. App Passwords can be set now, or later.

    Note: Email should be Thundermail address. Stalwart does not need your recovery email."""
    stalwart = MailClient()
    domain = email.split('@')[1]

    if domain != settings.PRIMARY_EMAIL_DOMAIN:
        error = f'Cannot create Stalwart account with non-primary email domain: {domain}'
        logging.error(f'[create_stalwart_account] {error}')

        return {
            'oidc_id': oidc_id,
            'username': username,
            'email': email,
            'reason': error,
            'task_status': 'failed',
        }

    # Make sure we don't have anyone with this username
    try:
        stalwart.get_account(username)
        # It already exists? We should have caught that in our system.
        sentry_sdk.capture_message(
            (
                'Error: Username already exists!'
                f' Cannot create a Stalwart account with the username {username} for {email}.'
            ),
            level='error',
            user={'oidc_id': oidc_id},
        )
        return {
            'oidc_id': oidc_id,
            'username': username,
            'email': email,
            'task_status': 'failed',
            'reason': 'Username already exists in Stalwart.',
        }
    except AccountNotFoundError:
        # We want this error
        pass

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
        print(f'checking domain {_domain}')
        _stalwart_check_or_create_domain_entry(stalwart, _domain)

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

    return {
        'oidc_id': oidc_id,
        'stalwart_pkid': pkid,
        'username': username,
        'email': email,
        'task_status': 'success',
    }
