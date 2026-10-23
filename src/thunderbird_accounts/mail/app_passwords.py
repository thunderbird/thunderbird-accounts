"""Support for the named app password manager (list / create / revoke) backed by Stalwart's x:AppPassword JMAP methods.

Everything here operates on the user's own JMAP account, so ownership is enforced by the credential used to talk to
Stalwart rather than by comparing ids across users.
"""

import logging
import unicodedata
from functools import wraps

import sentry_sdk
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from requests.exceptions import HTTPError
from rest_framework.response import Response

from thunderbird_accounts.authentication.middleware import get_user_access_token
from thunderbird_accounts.mail.clients.mail_client_jmap import MailClientUserJMAP
from thunderbird_accounts.mail.exceptions import MAIL_CLIENT_ERRORS
from thunderbird_accounts.mail.types.stalwart import AppPassword


#: Everything a user-scoped JMAP call can raise, including the client's own RuntimeError/ValueError shape checks.
APP_PASSWORD_CLIENT_ERRORS = MAIL_CLIENT_ERRORS + (RuntimeError, ValueError)


class AppPasswordNameError(ValueError):
    """The submitted app password name failed validation; ``message`` is safe to show to the user."""

    def __init__(self, message):
        super().__init__(str(message))
        self.message = str(message)


def is_internal_app_password(description: str | None) -> bool:
    """Credentials the product manages on the user's behalf (Appointment CalDAV) never appear in, or leave via, the
    manager."""
    return bool(description) and description.lower().startswith(settings.APPOINTMENT_APP_PASSWORD_PREFIX.lower())


def visible_app_passwords(credentials: list[AppPassword]) -> list[AppPassword]:
    return [
        credential
        for credential in credentials
        if credential.id and not is_internal_app_password(credential.description)
    ]


def serialize_app_password(credential: AppPassword) -> dict:
    """Metadata only: the hash Stalwart stores under ``secret`` must never reach the client."""
    return {
        'id': credential.id,
        'name': credential.description or '',
        'createdAt': credential.created_at.isoformat() if credential.created_at else None,
    }


def parse_app_password_name(data) -> str:
    """Validate the ``name`` of a create request and return it stripped.

    :raises AppPasswordNameError: with a user-facing message.
    """
    if not isinstance(data, dict):
        raise AppPasswordNameError(_('Invalid request data'))

    name = data.get('name')
    if not isinstance(name, str):
        raise AppPasswordNameError(_('Enter a name for this app password.'))

    name = name.strip()
    if not name:
        raise AppPasswordNameError(_('Enter a name for this app password.'))

    if len(name) > settings.APP_PASSWORD_NAME_MAX_LENGTH:
        raise AppPasswordNameError(
            _('Use no more than %(max_length)d characters for the app password name.')
            % {'max_length': settings.APP_PASSWORD_NAME_MAX_LENGTH}
        )

    if any(unicodedata.category(character).startswith('C') for character in name):
        raise AppPasswordNameError(_('The app password name contains unsupported characters.'))

    if is_internal_app_password(name):
        raise AppPasswordNameError(_('That app password name is reserved.'))

    return name


def app_password_error_response(error: Exception, fallback_message) -> Response:
    """Keep expired sessions distinct from service failures at every JMAP request stage."""
    if isinstance(error, HTTPError) and error.response is not None and error.response.status_code == 401:
        return Response(
            {'success': False, 'error': str(_('Your session has expired. Please sign in again.'))},
            status=401,
        )

    logging.warning('[app_password_error_response] %s: %s', fallback_message, error)
    sentry_sdk.capture_exception(error)
    return Response({'success': False, 'error': str(fallback_message)}, status=502)


def app_password_management_required(view_func):
    """Require the JMAP backend and hand a DRF route a user-scoped client as ``jmap_client``.

    Stack this inside ``api_view`` / ``permission_classes`` and ``active_subscription_required`` so it only ever sees
    an authenticated subscriber.
    """

    @wraps(view_func)
    def _view_wrapper(request, *args, **kwargs):
        if not settings.STALWART_ADMIN_API_USE_JMAP:
            # The manager relies on Stalwart generating and listing credentials, which the legacy admin api cannot do.
            return Response({'success': False, 'error': str(_('Not found'))}, status=404)

        primary_email = request.user.stalwart_primary_email
        if not primary_email:
            return Response(
                {
                    'success': False,
                    'error': str(_('Thundermail account setup is still in progress. Please try again shortly.')),
                    'code': 'mail_account_not_ready',
                },
                status=409,
            )

        access_token = get_user_access_token(request)
        if not access_token:
            return Response(
                {'success': False, 'error': str(_('Your session has expired. Please sign in again.'))},
                status=401,
            )

        try:
            jmap_client = MailClientUserJMAP(primary_email, access_token)
        except APP_PASSWORD_CLIENT_ERRORS as ex:
            return app_password_error_response(ex, _('Could not connect to Thundermail, please try again later.'))

        return view_func(request, *args, jmap_client=jmap_client, **kwargs)

    return _view_wrapper
