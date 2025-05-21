import datetime
import logging

from celery import shared_task
from django.core.signing import Signer, BadSignature

from thunderbird_accounts.subscription.models import Transaction, Subscription


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

    status = event_data.get('status')
    customer_id = event_data.get('customer_id')
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

    if next_billed_at:
        next_billed_at = datetime.datetime.fromisoformat(next_billed_at)

    current_billing_period = event_data.get('current_billing_period', {})
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
        },
    )

    return {
        'paddle_id': paddle_id,
        'occurred_at': occurred_at,
        'task_status': 'success',
        'model_uuid': subscription.uuid,
        'model_created': subscription_created,
    }
