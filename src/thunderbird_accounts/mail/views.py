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
        raise ValidationError(_("Required fields are not set"))
    if request.POST['email_domain'] not in settings.ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(_("Invalid domain selected"))

    email_address = f'{request.POST['email_address']}@{request.POST['email_domain']}'

    print("Making a guy!")

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


def self_serve(request: HttpRequest):
    return HttpResponseRedirect(reverse('self_serve_connection_info'))


def self_serve_connection_info(request: HttpRequest):
    if request.user.is_anonymous:
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

    account = request.user.account_set.first()

    return TemplateResponse(
        request,
        'mail/self-serve/connection-info.html',
        {
            'mail_username': account.name,
            'IMAP': settings.CONNECTION_INFO['IMAP'],
            'JMAP': settings.CONNECTION_INFO['JMAP'] if 'JMAP' in settings.CONNECTION_INFO else {},
            'SMTP': settings.CONNECTION_INFO['SMTP'],
        },
    )


def self_serve_app_passwords(request: HttpRequest):
    if request.user.is_anonymous:
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

    account = request.user.account_set.first()
    app_passwords = account.app_passwords

    return TemplateResponse(
        request,
        'mail/self-serve/app-passwords.html',
        {
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
