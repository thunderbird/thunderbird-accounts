import json
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib.auth.hashers import make_password, identify_hasher
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from thunderbird_accounts.authentication.templatetags.helpers import get_admin_login_code


# Create your views here.


def home(request: HttpRequest):
    return TemplateResponse(request, 'mail/index.html', {})


def self_serve(request: HttpRequest):
    return HttpResponseRedirect(reverse('self_serve_connection_info'))


def self_serve_connection_info(request: HttpRequest):
    if request.user.is_anonymous:
        return HttpResponseRedirect(
            reverse('fxa_login', kwargs={'login_code': get_admin_login_code(), 'redirect_to': quote_plus(request.path)})
        )

    account = request.user.account_set.first()

    return TemplateResponse(request, 'mail/self-serve/connection-info.html', {
        'mail_username': account.name,
        'IMAP': settings.CONNECTION_INFO['IMAP'],
        'JMAP': settings.CONNECTION_INFO['JMAP'] if 'JMAP' in settings.CONNECTION_INFO else {},
        'SMTP': settings.CONNECTION_INFO['SMTP']
    })


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
    print(request.POST)
    return JsonResponse({'success': True})


@require_http_methods(['POST'])
@sensitive_post_parameters('password')
def self_serve_app_password_add(request: HttpRequest):
    label = request.POST['name']
    password = make_password(request.POST['password'], hasher='argon2')

    if not label or not password:
        ValidationError('Label and password are required')

    hash_algo = identify_hasher(password)

    # We need to strip out the leading argon2$ from the hashed value
    if hash_algo.algorithm == 'argon2':
        _, password = password.split('argon2$')
        # Note: This is an intentional $, not a failed javascript template literal
        password = f'${password}'
    else:
        ValidationError('Unsupported algorithm')

    secret_string = f'$app${label}${password}'

    account = request.user.account_set.first()
    account.secret = secret_string
    account.save()

    return HttpResponseRedirect('/self-serve/app-passwords')


def wait_list(request: HttpRequest):
    return TemplateResponse(request, 'mail/wait-list.html', {
        'form_action': settings.WAIT_LIST_FORM_ACTION
    })
