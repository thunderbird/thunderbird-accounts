from typing import Optional

from django.contrib.auth.hashers import make_password, identify_hasher

from thunderbird_accounts import settings
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail import tasks


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


def decode_app_password(secret):
    if not secret:
        return ''

    # We only care about the app password name here
    return secret.replace('$app$', '').split('$')[0]


def create_stalwart_account(user, app_password: Optional[str] = None) -> bool:
    # Run this immediately for now, in the future we'll ship these to celery
    task_data = tasks.create_stalwart_account.run(
        oidc_id=user.oidc_id, username=user.username, email=user.username, app_password=app_password
    )

    if not task_data or task_data.get('task_status') == 'failed':
        return False

    return True


def add_email_addresses_to_stalwart_account(user: User, emails):
    tasks.add_email_addresses_to_stalwart_account.delay(username=user.username, emails=emails)


def replace_email_addresses_on_stalwart_account(user: User, emails):
    tasks.replace_email_addresses_on_stalwart_account.delay(username=user.username, emails=emails)


def delete_email_addresses_from_stalwart_account(user: User, emails):
    tasks.delete_email_addresses_from_stalwart_account.delay(username=user.username, emails=emails)


def is_allowed_domain(email_address: str) -> bool:
    """Pass in an email address and see if it's a valid / allowed email domain"""
    return any([email_address.endswith(domain) for domain in settings.ALLOWED_EMAIL_DOMAINS])
