import datetime
import json
import logging
import time

import sentry_sdk
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.core.signing import Signer

from paddle_billing import Client
from paddle_billing.Resources.CustomerPortalSessions.Operations import CreateCustomerPortalSession
from paddle_billing.Resources.Notifications.Operations import ListNotifications

from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook
from thunderbird_accounts.subscription import tasks, models
from thunderbird_accounts.subscription.decorators import inject_paddle
from thunderbird_accounts.subscription.models import Plan, Price
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour


def prefilter_paddle_webhook(event_type: str, event_data: dict) -> bool:
    """Returns a boolean on whether the paddle webhook should be dispatched as a celery task or ignored."""

    # We only care about non-draft transactions
    if event_type == 'transaction.created' and event_data.get('status') == models.Transaction.StatusValues.DRAFT:
        return False

    return True


@login_required
@require_http_methods(['POST'])
def get_paddle_information(request: Request):
    signer = Signer()

    plan_info = []
    plans = Plan.objects.filter(visible_on_subscription_page=True).exclude(product_id__isnull=True).all()
    for plan in plans:
        prices = plan.product.price_set.filter(status=Price.StatusValues.ACTIVE).all()
        plan_info.append({'name': plan.name, 'prices': [price.paddle_id for price in prices]})
        plan_info.extend([price.paddle_id for price in prices])

    return JsonResponse(
        {
            'paddle_token': settings.PADDLE_TOKEN,
            'paddle_environment': settings.PADDLE_ENV,
            'paddle_plan_info': plan_info,
            'signed_user_id': signer.sign(request.user.uuid.hex),
        }
    )


@login_required
@require_http_methods(['POST'])
@inject_paddle
def notify_paddle_checkout_complete(request: Request, paddle: Client):
    data = json.loads(request.body.decode())
    transaction_id = data.get('transactionId')

    print(data, transaction_id, request.body)
    if not transaction_id:
        return JsonResponse({'success': False})

    # Give paddle some time to update their end
    # Yes this is not perfect, I know.
    time.sleep(5)

    # We can't get webhook events on dev, so we need to manually check the event stream
    if settings.IS_DEV:
        subscription_id = None
        notification_list = paddle.notifications.list(ListNotifications(filter=transaction_id))

        # First look for the transaction
        for notification in notification_list:
            # Normalize the data to dict then a json blob then back to a dict.
            notification_data = json.loads(paddle.serialize_json_payload(notification.payload.data.to_dict()))
            if (
                notification_data.get('id') == transaction_id
                and notification.type == 'transaction.updated'
                and notification_data.get('status') == 'completed'
            ):
                tasks.paddle_transaction_event.run(notification_data, notification.occurred_at, is_create_event=True)
                subscription_id = notification_data.get('subscription_id')
                break

        # If we've found the transaction then we should have the subscription_id
        if subscription_id:
            subscription_list = paddle.notifications.list(ListNotifications(filter=subscription_id))

            # Look up the subscription now
            for notification in subscription_list:
                notification_data = json.loads(paddle.serialize_json_payload(notification.payload.data.to_dict()))
                # The serialization trick is not perfect, we need to flatten custom_data
                notification_data['custom_data'] = notification_data.get('custom_data', {}).get('data', {})

                if notification_data.get('id') == subscription_id and notification.type == 'subscription.created':
                    tasks.paddle_subscription_event.run(
                        notification_data,
                        notification.occurred_at,
                        is_create_event=True,
                    )
                    break

    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
@inject_paddle
def get_paddle_portal_link(request: Request, paddle: Client):
    if not request.user.has_active_subscription:
        return JsonResponse({}, status=401)

    subscription = request.user.subscription_set.first()
    customer_session = paddle.customer_portal_sessions.create(
        subscription.paddle_customer_id, CreateCustomerPortalSession()
    )
    return JsonResponse({'url': customer_session.urls.general.overview})


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
