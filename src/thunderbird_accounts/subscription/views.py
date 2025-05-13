import datetime

import sentry_sdk

from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook
from thunderbird_accounts.subscription import tasks
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour


@api_view(['POST'])
@authentication_classes([IsValidPaddleWebhook])
def handle_paddle_webhook(request: Request):
    data = request.data
    event_type = data.get('event_type')
    event_data: dict | None = data.get('event_data')
    occurred_at: str | None = data.get('occurred_at')

    if not event_data:
        sentry_sdk.set_context('request_data', data)
        raise UnexpectedBehaviour('Paddle webhook is empty')

    if not occurred_at:
        # Delete the event_data struct as we don't need to send all that data up.
        cloned_data: dict = data.copy()
        cloned_data.pop('event_data', '')
        sentry_sdk.set_context('request_data', cloned_data)

    occurred_at: datetime.datetime = datetime.datetime.fromisoformat(occurred_at)

    match event_type:
        case 'transaction.created':
            tasks.paddle_transaction_created.delay(event_data, occurred_at)
