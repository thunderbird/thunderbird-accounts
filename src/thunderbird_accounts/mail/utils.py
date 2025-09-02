from django.contrib.auth.hashers import make_password, identify_hasher
from thunderbird_accounts.mail import tasks
from thunderbird_accounts.mail.models import Account, Email


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


def create_stalwart_account(user):
    # Run this immediately for now, in the future we'll ship these to celery
    tasks.create_stalwart_account.run(
        user_uuid=user.uuid.hex, username=user.username, email=user.email
    )

    # Also create their account objects
    account = Account.objects.create(
        name=user.username,
        active=True,
        user=user,
    )
    Email.objects.create(address=user.username, type='primary', account=account)


def add_email_address_to_stalwart_account(user, email):
    # Run this immediately for now, in the future we'll ship these to celery
    tasks.add_email_address_to_stalwart_account.run(
        username=user.username, email=email
    )
