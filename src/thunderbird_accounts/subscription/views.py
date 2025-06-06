import datetime
import logging

import sentry_sdk
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook
from thunderbird_accounts.subscription import tasks, models
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour


def prefilter_paddle_webhook(event_type: str, event_data: dict) -> bool:
    """Returns a boolean on whether the paddle webhook should be dispatched as a celery task or ignored."""

    # We only care about non-draft transactions
    if event_type == 'transaction.created' and event_data.get('status') == models.Transaction.StatusValues.DRAFT:
        return False

    return True


@api_view(['POST'])
@authentication_classes([IsValidPaddleWebhook])
def handle_paddle_webhook(request: Request):
    response = HttpResponse(content=_('Thank you!'), status=200)

    data = request.data
    event_type: str = data.get('event_type')
    event_data: dict | None = data.get('data')
    occurred_at: str | None = data.get('occurred_at')

    logging.debug(f'Received {event_type} from Paddle')

    if not event_data:
        sentry_sdk.set_context('request_data', data)
        raise UnexpectedBehaviour('Paddle webhook is empty')

    if not occurred_at:
        # Delete the event_data struct as we don't need to send all that data up.
        cloned_data: dict = data.copy()
        cloned_data.pop('data', '')
        sentry_sdk.set_context('request_data', cloned_data)
        raise UnexpectedBehaviour('Paddle webhook is missing occurred at')

    occurred_at: datetime.datetime = datetime.datetime.fromisoformat(occurred_at)

    # Don't dispatch celery tasks if we know they're going to be ignored
    if not prefilter_paddle_webhook(event_type, event_data):
        logging.debug(f'Ignored {event_type} webhook')
        return response

    is_create_event = event_type.endswith('.created')

    if event_type == 'transaction.created' or event_type == 'transaction.updated':
        tasks.paddle_transaction_event.delay(event_data, occurred_at, is_create_event=is_create_event)
    elif event_type == 'subscription.created' or event_type == 'subscription.updated':
        tasks.paddle_subscription_event.delay(event_data, occurred_at, is_create_event=is_create_event)
    elif event_type == 'product.created' or event_type == 'product.updated':
        tasks.paddle_product_event.delay(event_data, occurred_at, is_create_event=is_create_event)
    else:
        logging.debug(f"Skipping {event_type} as it's not supported")

    logging.debug(f'Dispatched {event_type} webhook')
    return response
