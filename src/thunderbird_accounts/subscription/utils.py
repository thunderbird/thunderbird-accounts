from django.conf import settings

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.subscription.models import Plan


def calculate_quota_in_bytes(value_in_gb: int):
    """Convert our plan's quota field (in gb) to bytes for Stalwart."""
    return value_in_gb * settings.ONE_GIGABYTE_IN_BYTES


def update_user_mail_quota(user: User, plan: Plan):
    """Updates a user's mail accounts quota."""
    accounts = user.account_set.all()
    for account in accounts:
        account.quota = calculate_quota_in_bytes(plan.mail_storage_gb)
        account.save()
