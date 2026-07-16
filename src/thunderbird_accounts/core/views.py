from thunderbird_accounts.core.utils import get_feature_flags
from thunderbird_accounts.subscription.utils import get_visible_plan_info
from thunderbird_accounts.authentication.exceptions import AuthenticationUnavailable
from gettext import gettext
import sys
import json
import requests

import requests.exceptions
import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.messages import get_messages

from thunderbird_accounts.mail.clients import MailClient
from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
)
from thunderbird_accounts.mail.utils import decode_app_password, filter_app_passwords

from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse


def handle_500(request: HttpRequest, template_name=None):
    """Overrides Django's default 500 error page with our own"""
    # Retrieve the last known exception
    last_exception = sys.exc_info()[1]

    error_title = gettext('Unknown Error')
    if last_exception and isinstance(last_exception, AuthenticationUnavailable):
        error_title = gettext('Thunderbird Accounts is currently unavailable')

    # We ignore template_name and use our own here.
    return TemplateResponse(
        request,
        'errors/tbpro_500.html',
        {
            'error_title': error_title,
        },
        status=500,
    )


def home(request: HttpRequest):
    """The main route for our VueJS app.
    This prepares some data for the initial form load (like authentication information, plan information, and the like.)
    """
    app_passwords = []
    user_display_name = None
    custom_domains = []
    email_addresses = []
    max_custom_domains = None
    max_email_aliases = None
    needs_tos_acceptance = False
    recovery_email = request.user.recovery_email if request.user.is_authenticated else None

    # This state can only really happen when a user hits PermissionDenied immediately upon logging in.
    # They will be logged in via Keycloak and then a redirect loop will happen as we deny them permission,
    # redirect them to login. Since the store_token function occurs before the permission check, we can
    # use these conditions to ship the user to logout and thus "fixing" the redirect loop.
    if request.session.get('oidc_access_token') and not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('logout'))

    if request.user.is_authenticated and request.user.has_active_subscription:
        try:
            account = request.user.account_set.first()
            if not account:
                raise AccountNotFoundError(username=request.user.stalwart_primary_email)

            stalwart_client = MailClient()

            email_user = stalwart_client.get_account(request.user.stalwart_primary_email)
            user_display_name = email_user.get('description')

            # Get user's app passwords from Stalwart, excluding internal ones
            for secret in filter_app_passwords(email_user.get('secrets', [])):
                app_passwords.append(decode_app_password(secret))

            # Get user's email addresses from Stalwart
            email_addresses = email_user.get('emails', [])
        except AccountNotFoundError:
            app_passwords = []
            messages.error(request, _('Could not connect to Thundermail, please try again later.'))
        except requests.ConnectionError as ex:
            sentry_sdk.capture_exception(ex)
            messages.error(
                request,
                _('Thundermail is experiencing some connection issues, some aspects of the site may be unavailable.'),
            )

        # Get user's custom domains
        domains = request.user.domains.all()
        custom_domains = [
            {
                'name': domain.name,
                'status': domain.status,
            }
            for domain in domains
        ]

        # Get user's plan info constraints
        if request.user.plan:
            max_custom_domains = request.user.plan.mail_domain_count
            max_email_aliases = request.user.plan.mail_address_count
    elif not request.user.is_authenticated:  # Only if the user is not authenticated
        # Check if path is included in Vue's public routes (assets/app/vue/router.ts)
        public_routes = [
            '/privacy',
            '/terms',
            '/contact',
            '/sign-up',
            '/sign-up/complete',
            '/logout',
            '/error',
            '/chill',
        ]

        if request.path not in public_routes:
            return HttpResponseRedirect(reverse('login'))

    # Check if the user needs to accept the latest legal documents
    if request.user.is_authenticated:
        legal_doc_count = LegalDocument.objects.filter(is_current=True).count()
        accepted_current_doc_count = (
            LegalDocument.objects.filter(
                is_current=True,
                responses__user=request.user,
                responses__action=LegalDocumentResponse.Action.ACCEPTED,
            )
            .distinct()
            .count()
        )
        needs_tos_acceptance = legal_doc_count != accepted_current_doc_count

    form_data = request.session.get('form_data')
    if request.session.get('form_data'):
        # Clear form_data for any additional reloads
        request.session['form_data'] = {}

    return TemplateResponse(
        request,
        'index.html',
        {
            'connection_info': settings.CONNECTION_INFO,
            'app_passwords': json.dumps(app_passwords),
            'user_display_name': user_display_name,
            'allowed_domains': settings.ALLOWED_EMAIL_DOMAINS if settings.ALLOWED_EMAIL_DOMAINS else [],
            'custom_domains': json.dumps(custom_domains),
            'email_addresses': json.dumps(email_addresses),
            'max_custom_domains': max_custom_domains,
            'max_email_aliases': max_email_aliases,
            'tb_pro_appointment_url': settings.TB_PRO_APPOINTMENT_URL,
            'tb_pro_send_url': settings.TB_PRO_SEND_URL,
            'tb_pro_wait_list_url': settings.TB_PRO_WAIT_LIST_URL,
            'tb_pro_primary_domain': settings.PRIMARY_EMAIL_DOMAIN,
            'webmail_url': settings.WEBMAIL_URL,
            'server_messages': [
                {'level': message.level, 'message': str(message.message)} for message in get_messages(request)
            ],
            'form_data': form_data or None,
            'features': json.dumps(get_feature_flags()),
            'needs_tos_acceptance': needs_tos_acceptance,
            'recovery_email': recovery_email,
            'plan_info': get_visible_plan_info(),
            'paddle_token': settings.PADDLE_TOKEN,
            'paddle_environment': settings.PADDLE_ENV,
        },
    )
