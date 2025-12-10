import datetime
import json
import logging
import time

import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.core.signing import Signer

from paddle_billing import Client
from paddle_billing.Resources.CustomerPortalSessions.Operations import CreateCustomerPortalSession
from paddle_billing.Resources.Notifications.Operations import ListNotifications

from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook
from thunderbird_accounts.subscription import tasks
from thunderbird_accounts.subscription.decorators import inject_paddle
from thunderbird_accounts.subscription.models import Plan, Price, Subscription, Transaction
from thunderbird_accounts.utils.exceptions import UnexpectedBehaviour

# We only need this here right now
SESSION_PADDLE_TRANSACTION_ID = 'paddle_txid'


def prefilter_paddle_webhook(event_type: str, event_data: dict) -> bool:
    """Returns a boolean on whether the paddle webhook should be dispatched as a celery task or ignored."""

    # We only care about non-draft transactions
    if event_type == 'transaction.created' and event_data.get('status') == Transaction.StatusValues.DRAFT:
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
@require_http_methods(['PUT'])
def set_paddle_transaction_id(request: Request):
    """This error is used to work-around the fact we don't get a transaction id from Paddle's successUrl redirect.
    It kinda sucks, but it works for now."""
    if settings.IS_DEV:
        data = json.loads(request.body.decode())
        request.session[SESSION_PADDLE_TRANSACTION_ID] = data.get('txid')
    return JsonResponse({'success': True})


@login_required
@inject_paddle
def on_paddle_checkout_complete(request: Request, paddle: Client):
    transaction_id = request.session.pop(SESSION_PADDLE_TRANSACTION_ID, default=None)
    user = request.user
    if not user:
        sentry_sdk.capture_message(
            '[on_paddle_checkout_complete] User passed login_required but did not have user object!'
        )

        # I hope to never see this as it's technically impossible.
        messages.error(
            request,
            _('There was a problem verifying your user. Please re-login.'),
        )
        return HttpResponseRedirect('/')

    # The webhook could technically be processed before we get to this request, it's not likely to happen
    # but don't shoot ourselves in the foot if it does.
    if not user.has_active_subscription:
        user.is_awaiting_payment_verification = True
        user.save()

    # We can't get webhook events on dev, so we need to manually check the event stream
    if settings.IS_DEV:
        # Dev only error
        if not transaction_id:
            # Let's send them to the dashboard
            messages.error(
                request,
                _('The paddle transaction id was not in your session so we cannot pull the subscription information.'),
            )
            return HttpResponseRedirect('/subscribe')

        # Give paddle some time to update their end
        # Yes this is not perfect, I know.
        time.sleep(5)

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

    return HttpResponseRedirect('/dashboard')


@login_required
@require_http_methods(['POST'])
@inject_paddle
def get_paddle_portal_link(request: Request, paddle: Client):
    if not request.user.has_active_subscription:
        return JsonResponse({}, status=401)

    subscription = request.user.subscription_set.filter(status=Subscription.StatusValues.ACTIVE).first()
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


@login_required
@inject_paddle
@require_http_methods(['POST'])
def get_subscription_plan_info(request: Request, paddle: Client):
    """Returns the user's current subscription information including plan details, pricing, and features."""

    # Check if user has an active subscription
    if not request.user.has_active_subscription:
        return JsonResponse({'success': False, 'error': 'No active subscription found'}, status=404)

    # Get the user's active subscription
    subscription: Subscription = request.user.subscription_set.filter(status=Subscription.StatusValues.ACTIVE).first()

    if not subscription:
        return JsonResponse({'success': False, 'error': 'No active subscription found'}, status=404)

    # Get the subscription item (contains the product and price information)
    subscription_item = subscription.subscriptionitem_set.first()

    if not subscription_item or not subscription_item.product or not subscription_item.price:
        return JsonResponse({'success': False, 'error': 'Subscription information incomplete'}, status=500)

    # Get the plan from the user
    plan = request.user.plan

    if not plan:
        return JsonResponse({'success': False, 'error': 'Plan not found for user'}, status=500)

    price = subscription.current_billing_period_discounted_amount
    currency = subscription.current_billing_period_currency

    # Used quota comes from Stalwart and it is optional
    used_quota = None

    try:
        stalwart_client = MailClient()
        account = stalwart_client.get_account(request.user.stalwart_primary_email)
        quota = account.get('quota', 0)
        used_quota = account.get('used_quota', 0)
    except Exception as e:
        logging.error(f'Error getting used quota: {e}')
        return JsonResponse({'success': False, 'error': 'Error getting mail storage used quota'}, status=500)

    # Build the response
    subscription_info = {
        'name': plan.name,
        'description': subscription_item.product.description or '',
        'features': {
            'mailStorage': quota,  # The mail storage quota source of truth is Stalwart
            'sendStorage': plan.send_storage_bytes,
            'emailAddresses': plan.mail_address_count,
            'domains': plan.mail_domain_count,
        },
        'autoRenewal': subscription.next_billed_at,
        'usedQuota': used_quota,
        'price': price,
        'currency': currency,
        'period': subscription.subscriptionitem_set.first().price.billing_cycle_interval
        if subscription.subscriptionitem_set.count() > 0
        else 'year',
    }

    return JsonResponse({'success': True, 'subscription': subscription_info})
