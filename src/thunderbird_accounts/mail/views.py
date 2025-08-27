import base64
import json
import logging

import requests.exceptions
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.signing import Signer
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.client import MailClient, KeycloakClient
from thunderbird_accounts.mail.exceptions import AccessTokenNotFound
from thunderbird_accounts.mail.utils import decode_app_password

try:
    from paddle_billing import Client
    from paddle_billing.Resources.CustomerPortalSessions.Operations import CreateCustomerPortalSession
except ImportError:
    Client = None
    CreateCustomerPortalSession = None

from thunderbird_accounts.mail.models import Account, Email
from thunderbird_accounts.subscription.decorators import inject_paddle
from thunderbird_accounts.subscription.models import Plan, Price
from thunderbird_accounts.mail.zendesk import ZendeskClient
from thunderbird_accounts.mail import tasks, utils


def raise_form_error(request, to_view: str, error_message: str):
    """Puts the error message into the message bag and redirects to a named view."""
    messages.error(request, error_message, extra_tags='form-error')
    return HttpResponseRedirect(to_view)


def home(request: HttpRequest):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('self_serve_dashboard'))
    return TemplateResponse(request, 'mail/index.html', {})


@login_required
def sign_up(request: HttpRequest):
    # If we're posting ourselves, we're logging in
    if request.method == 'POST':
        return HttpResponseRedirect(reverse('self_serve_dashboard'))

    return TemplateResponse(
        request,
        'mail/sign-up/index.html',
        {
            'allowed_domains': settings.ALLOWED_EMAIL_DOMAINS,
            'cancel_redirect': reverse('self_serve_account_info'),
        },
    )


@require_http_methods(['POST'])
def sign_up_submit(request: HttpRequest):
    if request.user.is_anonymous:
        return HttpResponseRedirect('/')
    if len(request.user.account_set.all()) > 0:
        return raise_form_error(request, reverse('sign_up'), _('You already have an account'))
    if not request.POST['app_password'] or not request.POST['email_address'] or not request.POST['email_domain']:
        return raise_form_error(request, reverse('sign_up'), _('Required fields are not set'))
    if request.POST['email_domain'] not in settings.ALLOWED_EMAIL_DOMAINS:
        return raise_form_error(request, reverse('sign_up'), _('Invalid domain selected'))

    email_address = request.POST['email_address'].strip()
    email_address = f'{email_address}@{request.POST["email_domain"]}'

    try:
        Email.objects.get(address=email_address)
        return raise_form_error(request, reverse('sign_up'), _('Requested email is already taken'))
    except Email.DoesNotExist:
        pass

    user = request.user
    app_password = request.POST['app_password']

    # Send a task to create the inbox / account on stalwart's end
    if app_password:
        app_password = utils.save_app_password('Mail Client', app_password)

    # Run this immediately for now, in the future we'll ship these to celery
    tasks.create_stalwart_account.run(
        user_uuid=user.uuid.hex, username=email_address, email=user.email, app_password=app_password
    )

    account = Account.objects.create(
        name=email_address,
        active=True,
        user=request.user,
    )

    address = Email.objects.create(address=email_address, type='primary', account=account)

    if account and address:
        return HttpResponseRedirect(reverse('self_serve_dashboard'))

    return HttpResponseRedirect(reverse('sign_up'))


def self_serve_common_options(is_account_settings: bool, user: User, account: Account):
    """Common return params for self serve pages"""
    return {
        'has_account': True if account else False,
        'is_account_settings': is_account_settings,
        'has_active_subscription': user.has_active_subscription,
        'aia_url': settings.KEYCLOAK_AIA_ENDPOINT,
        'redirect_uri': f'{settings.PUBLIC_BASE_URL}{reverse('oidc_authentication_callback')}',
    }


def contact(request: HttpRequest):
    """Contact page for support requests (uses ZenDesk's API)
    A user can always access this page even if they don't have a mail account setup
    since they might encounter problems before the mail account setup itself."""
    return TemplateResponse(request, 'mail/contact.html')


@require_http_methods(['GET'])
def contact_fields(request: HttpRequest):
    """Get ticket fields from Zendesk API and filter for fields with custom options."""
    zendesk_client = ZendeskClient()
    result = zendesk_client.get_ticket_fields()

    if not result['success']:
        return JsonResponse(
            {'success': False, 'error': result.get('error', _('Failed to fetch ticket fields'))}, status=500
        )

    ticket_fields = result['data']['ticket_fields']
    fields_by_title = {}

    # Filter ticket fields to only include those with custom_field_options
    for field in ticket_fields:
        if 'custom_field_options' in field:
            # Extract the id, title, and custom_field_options with id, name and value
            field_data = {
                'id': field['id'],
                'title': field['title'],
                'custom_field_options': [
                    {'id': option['id'], 'name': option['name'], 'value': option['value']}
                    for option in field['custom_field_options']
                ],
            }
            fields_by_title[field['title']] = field_data

    return JsonResponse({'success': True, 'ticket_fields': fields_by_title})


@require_http_methods(['POST'])
def contact_submit(request: HttpRequest):
    """Uses Zendesk's Requests API to create a ticket
    Ref https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/#tickets-and-requests"""

    email = request.POST.get('email')
    subject = request.POST.get('subject')
    product = request.POST.get('product')
    product_field_id = request.POST.get('product_field_id')
    ticket_type = request.POST.get('type')
    type_field_id = request.POST.get('type_field_id')
    description = request.POST.get('description')
    uploaded_files = request.FILES.getlist('attachments')

    if not any([email, subject, product, ticket_type, description]):
        return raise_form_error(request, reverse('contact'), _('All fields are required'))

    # Upload files to Zendesk and collect tokens
    attachment_tokens = []
    zendesk_client = ZendeskClient()

    for uploaded_file in uploaded_files:
        try:
            zendesk_api_response = zendesk_client.upload_file(uploaded_file)

            if not zendesk_api_response['success']:
                return JsonResponse(
                    {
                        'success': False,
                        'error': _('Failed to upload file {uploaded_file_name}: {zendesk_api_response_error}').format(
                            uploaded_file_name=uploaded_file.name,
                            zendesk_api_response_error=zendesk_api_response.get('error', _('Unknown error')),
                        ),
                    },
                    status=500,
                )

            attachment_tokens.append(
                {'token': zendesk_api_response['upload_token'], 'filename': zendesk_api_response['filename']}
            )

        except Exception as e:
            return JsonResponse(
                {
                    'success': False,
                    'error': _('Failed to upload file {uploaded_file_name}: {error}').format(
                        uploaded_file_name=uploaded_file.name, error=str(e)
                    ),
                },
                status=500,
            )

    # Create ticket with attachment tokens
    ticket_fields = {
        'email': email,
        'subject': subject,
        'product': product,
        'product_field_id': product_field_id,
        'ticket_type': ticket_type,
        'type_field_id': type_field_id,
        'description': description,
        'attachments': attachment_tokens,
    }

    zendesk_api_response = zendesk_client.create_ticket(ticket_fields)

    if zendesk_api_response.ok:
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=500)

@login_required
def self_serve_account_settings(request: HttpRequest):
    """Account Settings page for Self Serve
    A user can always access this page even if they don't have a mail account setup.
    This way they can delete their account if they wish, or create an account."""
    account = request.user.account_set.first()

    return TemplateResponse(
        request,
        'mail/self-serve/account-info.html',
        self_serve_common_options(True, request.user, account),
    )


@login_required
def self_serve_dashboard(request: HttpRequest):
    """Connection Info page for Self Serve
    This page displays information relating to the connection settings
    that a user may need to connect an external mail client."""

    email = None
    account = request.user.account_set.first()
    if account:
        email = account.email_set.first()

    user = request.user

    kc = KeycloakClient()
    remote_credentials = kc.get_security_credentials(user.oidc_id)

    # Map the credentials to something like { password: { type: password, userLabel: null }, otp: { ... etc ... } }
    credentials = {cred.get('type'): {
        'type': cred.get('type'),
        'user_label': cred.get('userLabel')
    } for cred in remote_credentials}

    return TemplateResponse(
        request,
        'vue-base.html',
        {
            **self_serve_common_options(False, request.user, account),
            'mail_address': email.address if email else None,
            'mail_username': account.name if account else None,
            'IMAP': settings.CONNECTION_INFO['IMAP'],
            'JMAP': settings.CONNECTION_INFO['JMAP'] if 'JMAP' in settings.CONNECTION_INFO else {},
            'SMTP': settings.CONNECTION_INFO['SMTP'],
            'credentials': credentials,
        },
    )


@login_required
@inject_paddle
def self_serve_subscription(request: HttpRequest, paddle: Client):
    """Subscription page allowing user to select plan tier and do checkout via Paddle.js overlay

    This page requires a bit of setup before it can properly display:

    #. Have Paddle's (Sandbox or Production) API key set, and Paddle's client-side token setup.
    #. Pull a list of Paddle products and prices via the cli commands (these run on container boot.)
    #. At least one :any:`thunderbird_accounts.subscription.models.Plan` instance that's set up with a
        :any:`thunderbird_accounts.subscription.models.Product` relationship.

    """
    user = request.user
    account = request.user.account_set.first()
    signer = Signer()

    if user.has_active_subscription:
        subscription = user.subscription_set.first()

        customer_session = paddle.customer_portal_sessions.create(
            subscription.paddle_customer_id, CreateCustomerPortalSession()
        )
        return HttpResponseRedirect(customer_session.urls.general.overview)

    plan_info = []
    plans = Plan.objects.filter(visible_on_subscription_page=True).exclude(product_id__isnull=True).all()
    for plan in plans:
        prices = plan.product.price_set.filter(status=Price.StatusValues.ACTIVE).all()
        plan_info.extend([price.paddle_id for price in prices])

    return TemplateResponse(
        request,
        'mail/self-serve/subscription.html',
        {
            'is_subscription': True,
            'success_redirect': reverse('self_serve_subscription_success'),
            'paddle_token': settings.PADDLE_TOKEN,
            'paddle_environment': settings.PADDLE_ENV,
            'paddle_plan_info': json.dumps(plan_info),
            'signed_user_id': signer.sign(request.user.uuid.hex),
            **self_serve_common_options(False, request.user, account),
        },
    )


@login_required
def self_serve_subscription_success(request: HttpRequest):
    """Subscription page allowing user to select plan tier and do checkout via Paddle.js overlay"""
    account = request.user.account_set.first()
    return TemplateResponse(
        request,
        'mail/self-serve/subscription-success.html',
        {'is_subscription': True, **self_serve_common_options(False, request.user, account)},
    )


@login_required
def self_serve_app_passwords(request: HttpRequest):
    """App Password page for Self Serve
    A user can create (if none exists), or delete an App Password which is used to connect to the mail server."""
    account = request.user.account_set.first()

    stalwart_client = MailClient()
    email_user = stalwart_client.get_account(request.user.stalwart_username)

    app_passwords = []
    for secret in email_user.get('secrets', []):
        app_passwords.append(decode_app_password(secret))

    return TemplateResponse(
        request,
        'mail/self-serve/app-passwords.html',
        {
            **self_serve_common_options(False, request.user, account),
            'app_passwords': json.dumps(app_passwords),
        },
    )


@login_required
@require_http_methods(['POST'])
def self_serve_app_password_remove(request: HttpRequest):
    """Removes an app password from a remote Stalwart account"""
    app_password_label = json.loads(request.body).get('password')

    stalwart_client = MailClient()
    email_user = stalwart_client.get_account(request.user.stalwart_username)

    for secret in email_user.get('secrets', []):
        secret_label = decode_app_password(secret)
        if secret_label == app_password_label:
            stalwart_client.delete_app_password(request.user.stalwart_username, secret)
            return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@login_required
@require_http_methods(['POST'])
@sensitive_post_parameters('password')
def self_serve_app_password_add(request: HttpRequest):
    """Add an app password to the remote Stalwart account"""
    label = request.POST['name']
    password = request.POST['password']

    if not label or not password:
        return raise_form_error(request, reverse('self_serve_app_password'), _('Label and password are required'))

    stalwart_client = MailClient()
    email_user = stalwart_client.get_account(request.user.stalwart_username)
    for secret in email_user.get('secrets', []):
        secret_label = decode_app_password(secret)
        if secret_label == label:
            return raise_form_error(request, reverse('self_serve_app_password'), _('That label is already in-use'))

    secret = utils.save_app_password(label, password)
    stalwart_client.save_app_password(request.user.stalwart_username, secret)

    return HttpResponseRedirect('/self-serve/app-passwords')


def wait_list(request: HttpRequest):
    return TemplateResponse(request, 'mail/wait-list.html', {'form_action': settings.WAIT_LIST_FORM_ACTION})


@login_required
def jmap_test_page(request: HttpRequest):
    from thunderbird_accounts.mail.tiny_jmap_client import TinyJMAPClient

    """A test script that should not be ran in non-dev environments.
    This is based off the jmap spec sample code:
    https://github.com/fastmail/JMAP-Samples/blob/main/python3/top-ten.py"""
    user = request.user
    access_token = request.session['oidc_access_token']
    inboxes = []

    try:
        if not access_token:
            raise AccessTokenNotFound('Access token is not in session object. User may need to re-login.')

        client = TinyJMAPClient(
            hostname=settings.STALWART_BASE_JMAP_URL,
            username=user.username,
            token=access_token,
        )
        account_id = client.get_account_id()

        inbox_res = client.make_jmap_call(
            {
                'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
                'methodCalls': [
                    [
                        'Mailbox/query',
                        {
                            'accountId': account_id,
                            'filter': {'role': 'inbox', 'hasAnyRole': True},
                        },
                        'a',
                    ]
                ],
            }
        )
        inboxes = inbox_res['methodResponses'][0][1]['ids']
    except (AccessTokenNotFound, requests.exceptions.HTTPError, Exception) as ex:
        logging.error('Jmap test route failed')
        logging.exception(ex)

    return JsonResponse(
        {
            'jmap_url': f'{settings.STALWART_BASE_JMAP_URL}/.well-known/jmap',
            'username': user.username,
            'connection': len(inboxes) > 0,
        }
    )
