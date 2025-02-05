import json
from urllib.parse import quote_plus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.templatetags.helpers import get_admin_login_code
from thunderbird_accounts.mail.models import Account, Email


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
    print(request.POST)
    if request.user.is_anonymous:
        return HttpResponseRedirect('/')
    if len(request.user.account_set.all()) > 0:
        raise ValidationError(_('You already have an account'))
    if not request.POST['app_password'] or not request.POST['email_address'] or not request.POST['email_domain']:
        raise ValidationError(_('Required fields are not set'))
    if request.POST['email_domain'] not in settings.ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(_('Invalid domain selected'))

    email_address = f'{request.POST['email_address']}@{request.POST['email_domain']}'

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


def self_serve(request: HttpRequest):
    return HttpResponseRedirect(reverse('self_serve_connection_info'))


def self_serve_account_settings(request: HttpRequest):
    """Account Settings page for Self Serve
    A user can always access this page even if they don't have a mail account setup.
    This way they can delete their account if they wish, or create an account."""
    if request.user.is_anonymous:
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

    account = request.user.account_set.first()

    return TemplateResponse(
        request,
        'mail/self-serve/account-info.html',
        self_serve_common_options(True, account),
    )


def self_serve_connection_info(request: HttpRequest):
    """Connection Info page for Self Serve
    This page displays information relating to the connection settings
    that a user may need to connect an external mail client."""
    if request.user.is_anonymous:
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

    account = request.user.account_set.first()

    return TemplateResponse(
        request,
        'mail/self-serve/connection-info.html',
        {
            **self_serve_common_options(False, account),
            'mail_username': account.name if account else None,
            'IMAP': settings.CONNECTION_INFO['IMAP'],
            'JMAP': settings.CONNECTION_INFO['JMAP'] if 'JMAP' in settings.CONNECTION_INFO else {},
            'SMTP': settings.CONNECTION_INFO['SMTP'],
        },
    )


def self_serve_app_passwords(request: HttpRequest):
    """App Password page for Self Serve
    A user can create (if none exists), or delete an App Password which is used to connect to the mail server."""
    if request.user.is_anonymous:
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

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


@require_http_methods(['POST'])
def self_serve_app_password_remove(request: HttpRequest):
    if request.user.is_anonymous:
        return JsonResponse({'success': False})
    account = request.user.account_set.first()
    account.secret = None
    account.save()

    return JsonResponse({'success': True})


@require_http_methods(['POST'])
@sensitive_post_parameters('password')
def self_serve_app_password_add(request: HttpRequest):
    if request.user.is_anonymous:
        return JsonResponse({'success': False})

    label = request.POST['name']
    password = request.POST['password']

    if not label or not password:
        raise ValidationError('Label and password are required')

    account = request.user.account_set.first()
    if not account.save_app_password(label, password):
        raise ValidationError('Unsupported algorithm')

    return HttpResponseRedirect('/self-serve/app-passwords')


def wait_list(request: HttpRequest):
    return TemplateResponse(request, 'mail/wait-list.html', {
        'form_action': settings.WAIT_LIST_FORM_ACTION
    })
