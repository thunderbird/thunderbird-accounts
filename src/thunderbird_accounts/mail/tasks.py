import logging
from typing import Optional

import sentry_sdk
from celery import shared_task

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError


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


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def add_email_address_to_stalwart_account(self, username: str, email: str):
    stalwart = MailClient()
    domain = email.split('@')[1]

    try:
        # Make sure the domain is in stalwart, otherwise we can't save this address
        _stalwart_check_or_create_domain_entry(stalwart, domain)

        stalwart.save_email_address(username, email)
        return {
            'username': username,
            'email': email,
            'task_status': 'success',
        }
    except RuntimeError as ex:
        logging.error(f'[add_email_address_to_stalwart_account] Error adding email address to stalwart account {ex}')
        error = ex

    return {
        'username': username,
        'email': email,
        'reason': error,
        'task_status': 'failed',
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def create_stalwart_account(self, oidc_id: str, username: str, email: str, full_name: Optional[str] = None,
                            app_password: Optional[str] = None):
    """Creates a Stalwart Account with the given parameters. OIDC ID is currently just used for error logging,
    but is still required. App Passwords can be set now, or later.

    Note: Email should be Thundermail address. Stalwart does not need your recovery email."""
    stalwart = MailClient()
    domain = email.split('@')[1]

    # Make sure we don't have anyone with this username
    try:
        account = stalwart.get_account(username)

        # Make sure the account always has email in emails
        emails = account.get('emails', [])
        if email not in emails:
            # Make sure the domain is in stalwart, otherwise we can't save this address
            _stalwart_check_or_create_domain_entry(stalwart, domain)

            # Not in our account? We'll update the account and consider that a success.
            stalwart.save_email_address(username, email)
            return {
                'oidc_id': oidc_id,
                'stalwart_pkid': account.get('id'),
                'username': username,
                'email': email,
                'task_status': 'success',
            }

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

    _stalwart_check_or_create_domain_entry(stalwart, domain)

    # We need to create this after dkim and domain records exist
    pkid = stalwart.create_account(email, username, full_name, app_password)
    return {
        'oidc_id': oidc_id,
        'stalwart_pkid': pkid,
        'username': username,
        'email': email,
        'task_status': 'success',
    }
