from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.utils import create_stalwart_account, update_quota_on_stalwart_account
from thunderbird_accounts.subscription.models import Plan


def activate_subscription_features(user: User, plan: Plan):
    """Activates a plan.
    Which right now just saves the plan_id on the user, creates the mail account if one doesn't exist,
    or updates an existing mail account's quota."""
    if not user.has_active_subscription:
        return

    # Associate the plan id
    # We technically have a link through user -> subscriptions -> subscription items -> product -> plan
    # but that's too long...
    user.plan_id = plan.uuid
    user.save()

    # TODO: Save this in keycloak

    account = user.account_set.first()
    if account and account.stalwart_id:
        # Update the mail storage quota
        account.quota = plan.mail_storage_bytes
        account.save()

        update_quota_on_stalwart_account(user, account.quota)
        return

    create_stalwart_account(user, None)


def deactivate_subscription_features():
    """
    TODO: Implement me
    """
    pass
