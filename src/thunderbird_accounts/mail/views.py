import json
from urllib.parse import quote_plus

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

from thunderbird_accounts.authentication.templatetags.helpers import get_admin_login_code
from thunderbird_accounts.mail.models import Account, Email


def raise_form_error(request, to_view: str, error_message: str):
    """Puts the error message into the message bag and redirects to a named view."""
    messages.error(request, error_message, extra_tags='form-error')
    return HttpResponseRedirect(to_view)


def home(request: HttpRequest):
    return TemplateResponse(request, 'mail/index.html', {})


def sign_up(request: HttpRequest):
    # If we're posting ourselves, we're logging in
    if request.method == 'POST':
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

    return TemplateResponse(
        request,
        'mail/sign-up/index.html',
        {
            'allowed_domains': settings.ALLOWED_EMAIL_DOMAINS,
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

    account = Account.objects.create(
        name=request.user.email,
        type='individual',
        quota=0,
        active=True,
        django_user=request.user,
    )
    account.save_app_password('Mail Clients', request.POST['app_password'])

    address = Email.objects.create(address=email_address, type='primary', name=account)

    if account and address:
        return HttpResponseRedirect(reverse('self_serve_connection_info'))

    return HttpResponseRedirect(reverse('sign_up'))


def self_serve_common_options(is_account_settings: bool, account: Account):
    """Common return params for self serve pages"""
    return {'has_account': True if account else False, 'is_account_settings': is_account_settings}


@login_required
def self_serve(request: HttpRequest):
    return HttpResponseRedirect(reverse('self_serve_connection_info'))


@login_required
def self_serve_account_settings(request: HttpRequest):
    """Account Settings page for Self Serve
    A user can always access this page even if they don't have a mail account setup.
    This way they can delete their account if they wish, or create an account."""
    account = request.user.account_set.first()

    return TemplateResponse(
        request,
        'mail/self-serve/account-info.html',
        self_serve_common_options(True, account),
    )


@login_required
def self_serve_connection_info(request: HttpRequest):
    """Connection Info page for Self Serve
    This page displays information relating to the connection settings
    that a user may need to connect an external mail client."""

    email = None
    account = request.user.account_set.first()
    if account:
        email = account.email_set.first()

    return TemplateResponse(
        request,
        'mail/self-serve/connection-info.html',
        {
            **self_serve_common_options(False, account),
            'mail_address': email.address if email else None,
            'mail_username': account.name if account else None,
            'IMAP': settings.CONNECTION_INFO['IMAP'],
            'JMAP': settings.CONNECTION_INFO['JMAP'] if 'JMAP' in settings.CONNECTION_INFO else {},
            'SMTP': settings.CONNECTION_INFO['SMTP'],
        },
    )


@login_required
def self_serve_subscription(request: HttpRequest):
    """Subscription page allowing user to select plan tier and do checkout via Paddle.js overlay"""
    account = request.user.account_set.first()
    signer = Signer()
    return TemplateResponse(
        request,
        'mail/self-serve/subscription.html',
        {
            'is_subscription': True,
            'success_redirect': reverse('self_serve_subscription_success'),
            'paddle_token': settings.PADDLE_TOKEN,
            'paddle_environment': settings.PADDLE_ENV,
            'paddle_price_id_lo': settings.PADDLE_PRICE_ID_LO,
            'paddle_price_id_md': settings.PADDLE_PRICE_ID_MD,
            'paddle_price_id_hi': settings.PADDLE_PRICE_ID_HI,
            'signed_user_id': signer.sign(request.user.uuid.hex),
            **self_serve_common_options(False, account),
        },
    )


@login_required
def self_serve_subscription_success(request: HttpRequest):
    """Subscription page allowing user to select plan tier and do checkout via Paddle.js overlay"""
    account = request.user.account_set.first()
    return TemplateResponse(
        request,
        'mail/self-serve/subscription-success.html',
        {'is_subscription': True, **self_serve_common_options(False, account)},
    )


@login_required
def self_serve_app_passwords(request: HttpRequest):
    """App Password page for Self Serve
    A user can create (if none exists), or delete an App Password which is used to connect to the mail server."""
    account = request.user.account_set.first()
    app_passwords = account.app_passwords if account else []

    return TemplateResponse(
        request,
        'mail/self-serve/app-passwords.html',
        {
            **self_serve_common_options(False, account),
            'app_passwords': json.dumps(app_passwords),
        },
    )


@login_required
@require_http_methods(['POST'])
def self_serve_app_password_remove(request: HttpRequest):
    if request.user.is_anonymous:
        return JsonResponse({'success': False})
    account = request.user.account_set.first()
    account.secret = None
    account.save()

    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
@sensitive_post_parameters('password')
def self_serve_app_password_add(request: HttpRequest):
    if request.user.is_anonymous:
        return JsonResponse({'success': False})

    label = request.POST['name']
    password = request.POST['password']

    if not label or not password:
        return raise_form_error(request, reverse('self_serve_app_password'), _('Label and password are required'))

    account = request.user.account_set.first()
    if not account.save_app_password(label, password):
        return raise_form_error(request, reverse('self_serve_app_password'), _('Unsupported algorithm'))

    return HttpResponseRedirect('/self-serve/app-passwords')


def wait_list(request: HttpRequest):
    return TemplateResponse(request, 'mail/wait-list.html', {'form_action': settings.WAIT_LIST_FORM_ACTION})
