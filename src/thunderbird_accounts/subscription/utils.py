from django.db import transaction as dj_transaction
from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.utils import create_stalwart_account, update_quota_on_stalwart_account
from thunderbird_accounts.subscription.models import Plan, Price


def get_visible_plan_info() -> dict | None:
    """Return the first subscription-page plan with active prices for frontend display."""
    plan = Plan.objects.filter(visible_on_subscription_page=True).exclude(product_id__isnull=True).first()

    if not plan:
        return None

    prices = plan.product.price_set.filter(status=Price.StatusValues.ACTIVE).all()

    return {
        'name': plan.name,
        'description': plan.product.description or '',
        'prices': [price.paddle_id for price in prices],
    }


def sync_plan_to_keycloak(user: User):
    """Sync the user's plan information according to the state of user.has_active_subscription.
    If they don't have an active subscription then they're not subscribed and can't access their services. Note that
    deactivating the plan (is_subscribed=False) will not adjust their plan information.

    If their plan is active then this will update their plan information as well as setting is_subscribed=True."""
    keycloak = KeycloakClient()

    if not user.has_active_subscription:
        keycloak.update_user_plan_info(user.oidc_id, is_subscribed=False)
        return

    keycloak.update_user_plan_info(
        user.oidc_id,
        is_subscribed=True,
        mail_address_count=user.plan.mail_address_count,
        mail_domain_count=user.plan.mail_domain_count,
        mail_storage_bytes=user.plan.mail_storage_bytes,
        send_storage_bytes=user.plan.send_storage_bytes,
    )


def activate_subscription_features(user: User, plan: Plan):
    """Activates a plan.
    Which right now just saves the plan_id on the user, creates the mail account if one doesn't exist,
    or updates an existing mail account's quota."""
    if not user.has_active_subscription:
        return

    # Associate the plan id and remove any payment verification flag
    # We technically have a link through user -> subscriptions -> subscription items -> product -> plan
    # but that's too long...
    # We also lock the user row for this update as it's pretty important
    with dj_transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.uuid)
        if locked_user.plan_id != plan.uuid:
            locked_user.plan_id = plan.uuid
        locked_user.is_awaiting_payment_verification = False
        locked_user.save()

    # Pull the updated user data from the transaction above
    user.refresh_from_db()

    # TODO: Temporarily removed until https://github.com/thunderbird/thunderbird-accounts/issues/346 is ready
    # sync_plan_to_keycloak(user)

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
