import datetime
import logging

from celery import shared_task
from django.core.signing import Signer, BadSignature

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.subscription.models import Transaction, Subscription, SubscriptionItem, Price, Product, Plan


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def paddle_transaction_event(self, event_data: dict, occurred_at: datetime.datetime, is_create_event: bool):
    """Handles transaction.created and transaction.updated events.
    Docs: https://developer.paddle.com/webhooks/transactions/transaction-created
    Docs: https://developer.paddle.com/webhooks/transactions/transaction-updated
    """
    paddle_id = event_data.get('id')

    try:
        query = Transaction.objects.filter(paddle_id=paddle_id)
        if not is_create_event:
            query = query.filter(webhook_updated_at__gt=occurred_at)
        transaction = query.get()
        if transaction:
            if is_create_event:
                err = (
                    f'Ignoring webhook as transaction (uuid={transaction.uuid}, paddle_id={paddle_id}) exists when '
                    f"it shouldn't exist."
                )
                reason = 'transaction already exists'
            else:
                err = (
                    f'Ignoring webhook as transaction (uuid={transaction.uuid}, paddle_id={paddle_id}) update was '
                    f'updated later than when the webhook occurred at.'
                )
                reason = 'webhook is out of date'

            logging.info(err)

            return {
                'paddle_id': paddle_id,
                'occurred_at': occurred_at,
                'task_status': 'failed',
                'reason': reason,
            }
    except Transaction.DoesNotExist:
        pass

    paddle_invoice_id = event_data.get('invoice_id')
    paddle_subscription_id = event_data.get('subscription_id')
    invoice_number = event_data.get('invoice_number')
    status = event_data.get('status')
    origin = event_data.get('origin')
    billed_at = event_data.get('billed_at')
    revised_at = event_data.get('revised_at')

    if billed_at:
        billed_at = datetime.datetime.fromisoformat(billed_at)
    if revised_at:
        revised_at = datetime.datetime.fromisoformat(revised_at)

    details = event_data.get('details')

    if not details or not details.get('totals'):
        logging.error(f'Transaction (paddle_id={paddle_id}) webhook contains no details or totals object.')
        return {
            'paddle_id': paddle_id,
            'occurred_at': occurred_at,
            'task_status': 'failed',
            'reason': 'no details or totals object',
        }

    totals = details.get('totals', {})
    total = totals.get('total')
    tax = totals.get('tax')
    currency = totals.get('currency_code')

    if total is None or tax is None or currency is None:
        logging.error(f'Transaction (paddle_id={paddle_id}) webhook contains invalid total, tax, or currency strings.')
        return {
            'paddle_id': paddle_id,
            'occurred_at': occurred_at,
            'task_status': 'failed',
            'reason': 'invalid total, tax, or currency strings',
        }

    # Okay now we can just do a big update.
    transaction, transaction_created = Transaction.objects.update_or_create(
        paddle_id=paddle_id,
        defaults={
            'paddle_invoice_id': paddle_invoice_id,
            'paddle_subscription_id': paddle_subscription_id,
            'invoice_number': invoice_number,
            'total': total,
            'tax': tax,
            'currency': currency,
            'status': status,
            'transaction_origin': origin,
            'billed_at': billed_at,
            'revised_at': revised_at,
            'webhook_updated_at': occurred_at,
        },
    )

    return {
        'paddle_id': paddle_id,
        'occurred_at': occurred_at,
        'task_status': 'success',
        'model_uuid': transaction.uuid,
        'model_created': transaction_created,
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def paddle_subscription_event(self, event_data: dict, occurred_at: datetime.datetime, is_create_event: bool):
    """Handles subscription.created events.
    Docs: https://developer.paddle.com/webhooks/subscriptions/subscription-created
    Docs: https://developer.paddle.com/webhooks/subscriptions/subscription-updated
    """
    paddle_id = event_data.get('id')

    try:
        query = Subscription.objects.filter(paddle_id=paddle_id)
        if not is_create_event:
            query = query.filter(webhook_updated_at__gt=occurred_at)
        subscription = query.get()
        if subscription:
            if is_create_event:
                err = (
                    f'Ignoring webhook as subscription (uuid={subscription.uuid}, paddle_id={paddle_id}) exists when '
                    f"it shouldn't exist."
                )
                reason = 'subscription already exists'
            else:
                err = (
                    f'Ignoring webhook as subscription (uuid={subscription.uuid}, paddle_id={paddle_id}) update was '
                    f'updated later than when the webhook occurred at.'
                )
                reason = 'webhook is out of date'

            logging.info(err)

            return {
                'paddle_id': paddle_id,
                'occurred_at': occurred_at,
                'task_status': 'failed',
                'reason': reason,
            }
    except Subscription.DoesNotExist:
        pass

    subscription_items = event_data.get('items', [])
    status = event_data.get('status')
    customer_id = event_data.get('customer_id')
    transaction_id = event_data.get('transaction_id')
    next_billed_at = event_data.get('next_billed_at')
    custom_data = event_data.get('custom_data', {}) or dict()
    signed_user_id = custom_data.get('signed_user_id')

    if not signed_user_id:
        logging.info(f'Ignoring webhook as subscription (paddle_id={paddle_id}) as no signed user id was provided.')
        return {
            'paddle_id': paddle_id,
            'occurred_at': occurred_at,
            'task_status': 'failed',
            'reason': 'no signed user id provided',
        }

    try:
        signer = Signer()
        user_uuid = signer.unsign(signed_user_id)
    except BadSignature:
        logging.info(
            f'Ignoring webhook as subscription (paddle_id={paddle_id}) as an invalid signed user id was provided.'
        )
        return {
            'paddle_id': paddle_id,
            'occurred_at': occurred_at,
            'task_status': 'failed',
            'reason': 'invalid signed user id provided (bad signature exception)',
        }

    try:
        user = User.objects.get(pk=user_uuid)
    except User.DoesNotExist:
        logging.error(f'Signed user uuid {user_uuid} is invalid! ')
        return {
            'paddle_id': paddle_id,
            'occurred_at': occurred_at,
            'user_uuid': user_uuid,
            'task_status': 'failed',
            'reason': 'invalid signed user id provided (no user found)',
        }

    if next_billed_at:
        next_billed_at = datetime.datetime.fromisoformat(next_billed_at)

    current_billing_period = event_data.get('current_billing_period', {})
    current_billing_period_starts_at = None
    current_billing_period_ends_at = None
    if current_billing_period:
        current_billing_period_starts_at = current_billing_period.get('starts_at')
        current_billing_period_ends_at = current_billing_period.get('end_at')

        if current_billing_period_starts_at:
            current_billing_period_starts_at = datetime.datetime.fromisoformat(current_billing_period_starts_at)

        if current_billing_period_ends_at:
            current_billing_period_ends_at = datetime.datetime.fromisoformat(current_billing_period_ends_at)

    subscription, subscription_created = Subscription.objects.update_or_create(
        paddle_id=paddle_id,
        defaults={
            'paddle_customer_id': customer_id,
            'status': status,
            'next_billed_at': next_billed_at,
            'current_billing_period_starts_at': current_billing_period_starts_at,
            'current_billing_period_ends_at': current_billing_period_ends_at,
            'user_id': user_uuid,
            'webhook_updated_at': occurred_at,
        },
    )

    # If a transaction_id is included, then update/create the association to this subscription
    if transaction_id:
        Transaction.objects.update_or_create(
            paddle_id=transaction_id,
            defaults={
                'paddle_subscription_id': paddle_id,
                'subscription_id': subscription.uuid,
            },
        )

    for item in subscription_items:
        # Note: These are reoccurring items only
        # Slurp up the subscription items, these are only created if all three items are new

        quantity = item.get('quantity')
        price = item.get('price')
        product = item.get('product')
        price_obj = None
        product_obj = None

        # If we have the data we can create a price object now and reference in the subscription item
        if price:
            unit_price = price.get('unit_price', {})
            billing_cycle = price.get('billing_cycle', {})
            price_obj, price_obj_created = Price.objects.update_or_create(
                paddle_id=price.get('id'),
                defaults={
                    'paddle_product_id': product.get('id'),
                    'name': price.get('name'),
                    'amount': unit_price.get('amount'),
                    'currency': unit_price.get('currency_code'),
                    'price_type': price.get('type'),
                    'status': price.get('status'),
                    'billing_cycle_frequency': billing_cycle.get('frequency'),
                    'billing_cycle_interval': billing_cycle.get('interval'),
                    'webhook_updated_at': occurred_at,
                },
            )

        if product:
            try:
                product_obj = Product.objects.filter(paddle_id=product.get('id')).get()
            except Product.DoesNotExist:
                product_obj = None
                logging.warning(f'Product {product.get("id")} does not exist in db!')

        if product_obj:
            # Update quota
            plan = product_obj.plan
            if not plan:
                logging.warning(f'Product {product.get("id")} has no plan attached!')

        SubscriptionItem.objects.update_or_create(
            paddle_price_id=price.get('id'),
            paddle_product_id=product.get('id'),
            paddle_subscription_id=paddle_id,
            subscription_id=subscription.uuid,
            price_id=price_obj.uuid if price_obj else None,
            product_id=product_obj.uuid if product_obj else None,
            defaults={'quantity': quantity},
        )

    user.is_awaiting_payment_verification = False
    user.save()

    return {
        'paddle_id': paddle_id,
        'occurred_at': occurred_at,
        'task_status': 'success',
        'model_uuid': subscription.uuid,
        'model_created': subscription_created,
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def paddle_product_event(self, event_data: dict, occurred_at: datetime.datetime, is_create_event: bool):
    """Handles product.created and product.updated events.
    Docs: https://developer.paddle.com/webhooks/products/product-created
    Docs: https://developer.paddle.com/webhooks/products/product-updated
    """
    paddle_id = event_data.get('id')

    try:
        query = Product.objects.filter(paddle_id=paddle_id)
        if not is_create_event:
            query = query.filter(webhook_updated_at__gt=occurred_at)
        product = query.get()
        if product:
            if is_create_event:
                err = (
                    f'Ignoring webhook as transaction (uuid={product.uuid}, paddle_id={paddle_id}) exists when '
                    f"it shouldn't exist."
                )
                reason = 'product already exists'
            else:
                err = (
                    f'Ignoring webhook as transaction (uuid={product.uuid}, paddle_id={paddle_id}) update was '
                    f'updated later than when the webhook occurred at.'
                )
                reason = 'webhook is out of date'

            logging.info(err)

            return {
                'paddle_id': paddle_id,
                'occurred_at': occurred_at,
                'task_status': 'failed',
                'reason': reason,
            }
    except Product.DoesNotExist:
        pass

    name = event_data.get('name')
    description = event_data.get('description')
    product_type = event_data.get('type')
    status = event_data.get('status')

    # Okay now we can just do a big update.
    product, product_created = Product.objects.update_or_create(
        paddle_id=paddle_id,
        defaults={
            'name': name,
            'description': description,
            'product_type': product_type,
            'status': status,
            'webhook_updated_at': occurred_at,
        },
    )

    return {
        'paddle_id': paddle_id,
        'occurred_at': occurred_at,
        'task_status': 'success',
        'model_uuid': product.uuid,
        'model_created': product_created,
    }


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def update_thundermail_quota(self, plan_uuid):
    """Since Stalwart only checks the db we have to manually propagate a plan change across the user's accounts."""
    try:
        plan = Plan.objects.get(pk=plan_uuid)
    except Plan.DoesNotExist:
        logging.error(f'Could not find Plan with pk={plan_uuid}!')
        return {
            'plan_uuid': plan_uuid,
            'task_status': 'failed',
            'reason': 'plan does not exist',
        }

    updated = 0
    skipped = 0

    if plan.product:
        for item in plan.product.subscriptionitem_set.all():
            # This actually can't happen due to db constraints, but covering our bases...
            if not item.subscription or not item.subscription.user:
                logging.warning(
                    f'Subscription not found, or subscription user not found for subscription item={item.uuid}'
                )
                skipped += 1
                continue

            user: User = item.subscription.user
            for account in user.account_set.all():
                account.quota = plan.mail_storage_bytes
                account.save()
                updated += 1

    return {
        'plan_uuid': plan_uuid,
        'task_status': 'success',
        'updated': updated,
        'skipped': skipped,
    }
