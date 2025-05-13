import datetime
import logging

from celery import shared_task

from thunderbird_accounts.subscription.models import Transaction


@shared_task(bind=True, retry_backoff=True, retry_backoff_max=60 * 60, max_retries=10)
def paddle_transaction_created(self, event_data: dict, occurred_at: datetime.datetime):
    """Handles transaction.created events.
    Docs: https://developer.paddle.com/webhooks/transactions/transaction-created
    """
    paddle_id = event_data.get('id')

    try:
        transaction = Transaction.objects.filter(paddle_id=paddle_id, webhook_updated_at__gt=occurred_at).get()
    except Transaction.DoesNotExist:
        transaction = None

    if transaction:
        logging.info(
            f'Ignoring webhook as transaction (uuid={transaction.uuid}, paddle_id={paddle_id}) update was updated later than when the webhook occurred at.'
        )
        return {
            'paddle_id': paddle_id,
            'occurred_at': occurred_at,
            'task_status': 'failed',
            'reason': 'webhook is out of date',
        }

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
