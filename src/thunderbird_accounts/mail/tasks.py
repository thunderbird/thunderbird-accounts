from typing import Optional

import sentry_sdk
from celery import shared_task

from thunderbird_accounts.mail.client import MailClient
from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def create_stalwart_account(self, user_uuid: str, username: str, email: str, app_password: Optional[str]):
    stalwart = MailClient()
    domain = email.split('@')[1]

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
            user=user_uuid,
        )
        return {
            'uuid': user_uuid,
            'username': username,
            'email': email,
            'task_status': 'failed',
            'reason': 'Username already exists in Stalwart.',
        }
    except AccountNotFoundError:
        # We want this error
        pass

    # Check if we have the domain
    try:
        domain = stalwart.get_domain(domain)
    except DomainNotFoundError:
        # The domain doesn't exist in our records, we'll need to create it first
        # And then the dkim record for the domain
        # Annoyingly they all return null...
        stalwart.create_domain(domain)
        stalwart.create_dkim(domain)

    # We need to create this after dkim and domain records exist
    pkid = stalwart.create_account(email, username, user_uuid, app_password)
    return {
        'uuid': user_uuid,
        'stalwart_pkid': pkid,
        'username': username,
        'email': email,
        'task_status': 'success',
    }
