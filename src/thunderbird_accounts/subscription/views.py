import datetime
import json
import logging
import sentry_sdk

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.core.signing import Signer
from django.template.response import TemplateResponse

from paddle_billing import Client
from paddle_billing.Resources.CustomerPortalSessions.Operations import CreateCustomerPortalSession
from paddle_billing.Notifications.Entities.Shared.PaymentMethodType import PaymentMethodType

from rest_framework.decorators import api_view, authentication_classes
from rest_framework.request import Request

from thunderbird_accounts.authentication.models import AllowListEntry
from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.authentication.permissions import IsValidPaddleWebhook
from thunderbird_accounts.subscription import tasks
from thunderbird_accounts.subscription.decorators import inject_paddle
from thunderbird_accounts.subscription.models import Plan, Price, Subscription, Transaction
from thunderbird_accounts.core.exceptions import UnexpectedBehaviour

# We only need this here right now
SESSION_PADDLE_TRANSACTION_ID = 'paddle_txid'
SESSION_PADDLE_PAYMENT_TYPE = str(PaymentMethodType.Card)


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
    discount_id = None

    allow_list_entry = AllowListEntry.objects.filter(user=request.user).first()
    if not allow_list_entry and request.user.recovery_email:
        allow_list_entry = AllowListEntry.objects.filter(email=request.user.recovery_email).first()

    if allow_list_entry:
        discount_id = allow_list_entry.discount_id

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
            'discount_id': discount_id,
        }
    )


@login_required
@require_http_methods(['PUT'])
def set_paddle_transaction_id(request: Request):
    """This error is used to work-around the fact we don't get a transaction id from Paddle's successUrl redirect.
    It kinda sucks, but it works for now."""
    data = json.loads(request.body.decode())
    request.session[SESSION_PADDLE_TRANSACTION_ID] = data.get('txid')
    request.session[SESSION_PADDLE_PAYMENT_TYPE] = data.get('payment_type')
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def is_paddle_transaction_done(request: Request):
    """Checks if the Paddle transaction has finished and returns True or False.
    Also cleans up transaction id once the transaction is completed."""
    transaction_id = request.session.get(SESSION_PADDLE_TRANSACTION_ID, default=None)
    user = request.user
    if user.is_awaiting_payment_verification:
        return JsonResponse({'status': Transaction.StatusValues.PAID.value})

    if not transaction_id:
        return JsonResponse({'status': 'no-id?'})

    status = Transaction.StatusValues.DRAFT.value

    transaction = Transaction.objects.filter(paddle_id=transaction_id).first()
    if transaction:
        status = transaction.status

    return JsonResponse({'status': status})


@login_required
@inject_paddle
def paddle_transaction_complete(request: HttpRequest, paddle: Client):
    """User is redirected by Paddle via the successUrl. This means we have a transaction that's paid or
    completed (noted as doneish.)

    There's some special logic for certain payment processors that open a pop-up window instead of
    redirecting to another page or completeing on page. Those processors are defined in code, and
    will redirect the pop-up window to a django template that _should_ immediately close the window.
    For those processors the doneish/redirect logic is handled in
    :any:`thunderbird_accounts.subscription.views.is_paddle_transaction_done`

    For regular payment processors like the default ``card`` we will simply redirect to the subscribe page.
    The front-end will handle if the check to see if the user's transaction and subscription has been pulled
    in our db via webhooks.
    """
    user = request.user
    transaction_id = request.session.pop(SESSION_PADDLE_TRANSACTION_ID)
    payment_type = request.session.pop(SESSION_PADDLE_PAYMENT_TYPE)
    redirect_response = HttpResponseRedirect('/subscribe')

    # Hmm this shouldn't happen...
    if not transaction_id or not payment_type:
        return redirect_response

    transaction = paddle.transactions.get(transaction_id=transaction_id)
    status = transaction.status.value

    if transaction and status in [Transaction.StatusValues.COMPLETED.value, Transaction.StatusValues.PAID.value]:
        # Only set enable payment verification mode if they don't have an active subscription
        # As the webhook could technically come in before or during this successUrl redirect...
        if not user.has_active_subscription:
            user.is_awaiting_payment_verification = True
            user.save()

        if settings.IS_DEV:
            tasks.dev_only_paddle_fake_webhook.delay(transaction_id=transaction_id, user_uuid=user.uuid.hex)

        """
        Paddle folks mentioned these are the types that open pop-up windows:
         * PayPal
         * Alipay
         * Bancontact
         * BLIK
         * iDEAL
         * MB WAY
         * South Korea local cards
         * Naver Pay, Kakao Pay, Samsung Pay, Payco
         * Pix
         * UPI
        """
        if payment_type in [
            PaymentMethodType.Paypal.value,
            # We don't use these, but for completeness' sake.
            PaymentMethodType.Alipay.value,
            PaymentMethodType.Bancontact.value,
            PaymentMethodType.Ideal.value,
            PaymentMethodType.KoreaLocal.value,
        ]:
            # Tell their window to close
            return TemplateResponse(
                request,
                'close_window.html',
                status=200,
            )

    return redirect_response


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
        used_quota = account.get('usedQuota', 0)
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
