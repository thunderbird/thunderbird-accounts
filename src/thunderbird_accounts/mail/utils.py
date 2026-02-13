import logging
import uuid
from typing import Optional
from requests.exceptions import HTTPError
from django.contrib.auth.hashers import make_password, identify_hasher
import sentry_sdk

from thunderbird_accounts import settings
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.models import Account
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

            # Note: If the request didn't work, it won't have temp_id in it,
            # or if it's malformed it'll raise a keyerror.
            if temp_id not in inbox_res['methodResponses'][0][1]['created']:
                raise Exception('Failed to create archive folder')

        # If we got here without an error, then we can mark this as verified
        account.verified_archive_folder = True
        account.save()

        return True
    except (HTTPError, Exception, KeyError) as ex:
        logging.error('fix_archive_folder failed!')
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
