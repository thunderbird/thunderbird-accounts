import json
import time
from urllib.parse import quote, urlencode, urlparse
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
import sentry_sdk
from requests.exceptions import RequestException

from thunderbird_accounts.authentication.clients import KeycloakClient
from thunderbird_accounts.authentication.exceptions import InvalidDomainError, ImportUserError
from thunderbird_accounts.authentication.mfa import (
    MFA_MANAGEMENT_AUTH_SESSION_KEY,
    create_otpauth_uri,
    create_totp_secret,
    format_totp_secret,
    generate_recovery_codes,
    has_recent_mfa_management_auth,
    make_pending_recovery_codes_cache_key,
    make_pending_totp_cache_key,
    validate_totp_code,
)
from thunderbird_accounts.authentication.utils import is_email_in_allow_list, KeycloakRequiredAction, is_email_reserved
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.serializers import UserProfileSerializer


class SignUpThrottle(UserRateThrottle):
    scope = 'sign_up'


class TotpConfirmThrottle(UserRateThrottle):
    scope = 'totp_confirm'


def _base_credential_fields(credential: dict, default_label) -> dict:
    return {
        'id': credential.get('id'),
        'label': credential.get('userLabel') or credential.get('user_label') or default_label,
        'createdDate': credential.get('createdDate'),
        'lastUsedDate': credential.get('lastUsedDate'),
    }


def serialize_totp_credentials(credentials: list[dict]) -> list[dict]:
    return [_base_credential_fields(credential, _('Authenticator app')) for credential in credentials]


def serialize_recovery_codes_credentials(credentials: list[dict]) -> list[dict]:
    """Serialize stored recovery-codes credentials for the management UI.

    Plaintext codes are never returned here — they're only available in the response
    to a regenerate request. We surface the metadata Keycloak stores in
    `credentialData` so the UI can show "X of Y remaining" without re-fetching.
    """
    serialized: list[dict] = []
    for credential in credentials:
        try:
            credential_data = json.loads(credential.get('credentialData') or '{}')
        except (TypeError, ValueError):
            credential_data = {}
        serialized.append(
            {
                **_base_credential_fields(credential, _('Recovery codes')),
                'totalCodes': credential_data.get('total'),
                'remainingCodes': credential_data.get('remaining'),
            }
        )
    return serialized


def _resolve_mfa_next_path(request: Request) -> str:
    """Return the path to redirect the user back to after they re-authenticate.

    Prefers the same-origin Referer of the request that triggered the reauth so
    we can route the user back where they came from. Falls back to
    ``MFA_DEFAULT_NEXT_PATH`` when the Referer is missing, cross-origin, or
    not a relative path.
    """
    default = settings.MFA_DEFAULT_NEXT_PATH
    referer = request.META.get('HTTP_REFERER', '')
    if not referer:
        return default

    try:
        parsed = urlparse(referer)
    except ValueError:
        return default

    if parsed.netloc and parsed.netloc != request.get_host():
        return default
    if not parsed.path.startswith('/'):
        return default

    return f'{parsed.path}?{parsed.query}' if parsed.query else parsed.path


def make_mfa_reauthentication_response(request: Request) -> Response:
    reauth_url = f'{reverse("mfa_reauth")}?{urlencode({"next": _resolve_mfa_next_path(request)})}'
    return Response(
        {
            'success': False,
            'error': _('Please sign in again before changing multi-factor authentication.'),
            'reauthUrl': reauth_url,
        },
        status=403,
    )


def require_recent_mfa_auth(request: Request) -> Response | None:
    if has_recent_mfa_management_auth(request.session):
        return None

    return make_mfa_reauthentication_response(request)


def require_recent_mfa_auth_if_totp_set(
    request: Request,
    totp_credentials: list[dict] | None = None,
) -> Response | None:
    """Returns a reauth response if the user has TOTP configured and lacks a
    recent MFA management auth, otherwise None.

    Pass `totp_credentials` to skip the Keycloak round-trip when the caller
    already fetched them.
    """
    if has_recent_mfa_management_auth(request.session):
        return None

    try:
        credentials = (
            totp_credentials
            if totp_credentials is not None
            else KeycloakClient().get_totp_credentials(request.user.oidc_id)
        )
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response(
            {'success': False, 'error': _('Could not load multi-factor authentication methods.')},
            status=502,
        )

    if credentials:
        return make_mfa_reauthentication_response(request)
    return None


@api_view(['POST'])
def get_user_profile(request: Request):
    if not request.user:
        raise NotAuthenticated()
    return Response(UserProfileSerializer(request.user).data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_mfa_methods(request: Request):
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    try:
        keycloak = KeycloakClient()
        totp_credentials = keycloak.get_totp_credentials(request.user.oidc_id)
        recovery_codes_credentials = keycloak.get_recovery_codes_credentials(request.user.oidc_id)
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response(
            {'success': False, 'error': _('Could not load multi-factor authentication methods.')},
            status=502,
        )

    if reauth_response := require_recent_mfa_auth_if_totp_set(request, totp_credentials=totp_credentials):
        return reauth_response

    return Response(
        {
            'success': True,
            'methods': {
                'authenticatorApp': {
                    'set': len(totp_credentials) > 0,
                    'credentials': serialize_totp_credentials(totp_credentials),
                },
                'recoveryCodes': {
                    'set': len(recovery_codes_credentials) > 0,
                    'credentials': serialize_recovery_codes_credentials(recovery_codes_credentials),
                },
            },
        }
    )


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def start_totp_setup(request: Request):
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauth_response := require_recent_mfa_auth_if_totp_set(request):
        return reauth_response

    secret = create_totp_secret()
    cache.set(make_pending_totp_cache_key(request.user.pk), {'secret': secret}, settings.MFA_SETUP_CACHE_TTL)

    account_name = request.user.username
    return Response(
        {
            'success': True,
            'secret': format_totp_secret(secret),
            'otpAuthUri': create_otpauth_uri(secret, account_name),
            'issuer': settings.MFA_TOTP_ISSUER,
            'accountName': account_name,
            'digits': settings.MFA_TOTP_DIGITS,
            'period': settings.MFA_TOTP_PERIOD,
            'algorithm': settings.MFA_TOTP_ALGORITHM_KEY,
        }
    )


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@throttle_classes([TotpConfirmThrottle])
def confirm_totp_setup(request: Request):
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauth_response := require_recent_mfa_auth_if_totp_set(request):
        return reauth_response

    code = request.data.get('code', '')
    pending_setup = cache.get(make_pending_totp_cache_key(request.user.pk))
    if not pending_setup:
        return Response(
            {'success': False, 'error': _('The authenticator setup expired. Please try again.')},
            status=400,
        )

    if not validate_totp_code(pending_setup['secret'], code):
        return Response({'success': False, 'error': _('The one-time code is invalid.')}, status=400)

    user_label = request.data.get('label') or _('Authenticator app')
    try:
        totp_credentials = KeycloakClient().replace_totp_credential(
            oidc_id=request.user.oidc_id,
            secret=pending_setup['secret'],
            user_label=str(user_label),
        )
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not save the authenticator app.')}, status=502)

    if request.data.get('logoutOtherSessions'):
        try:
            KeycloakClient().logout_user_sessions(request.user.oidc_id)
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)

    # A successful TOTP confirm is fresh proof of possession; grant management auth without OIDC step-up.
    request.session[MFA_MANAGEMENT_AUTH_SESSION_KEY] = int(time.time())

    cache.delete(make_pending_totp_cache_key(request.user.pk))
    return Response({'success': True, 'credentials': serialize_totp_credentials(totp_credentials)})


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def remove_totp_credential(request: Request, credential_id: str):
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauthentication_response := require_recent_mfa_auth(request):
        return reauthentication_response

    try:
        totp_credentials = KeycloakClient().get_totp_credentials(request.user.oidc_id)
        if credential_id not in [credential.get('id') for credential in totp_credentials]:
            return Response({'success': False, 'error': _('Authenticator app not found.')}, status=404)

        KeycloakClient().delete_credential(request.user.oidc_id, credential_id)
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not remove the authenticator app.')}, status=502)

    return Response({'success': True})


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def start_recovery_codes_setup(request: Request):
    """Generate a fresh set of recovery codes and cache them server-side without
    yet replacing the user's existing Keycloak credential.

    The plaintext codes are returned only here so the UI can display them once.
    Old codes (if any) remain valid until the user acknowledges they've saved the
    new ones and the corresponding `confirm` endpoint commits them to Keycloak.
    """
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauth_response := require_recent_mfa_auth_if_totp_set(request):
        return reauth_response

    raw_codes = generate_recovery_codes()
    cache.set(
        make_pending_recovery_codes_cache_key(request.user.pk),
        {'codes': raw_codes},
        settings.MFA_SETUP_CACHE_TTL,
    )
    return Response({'success': True, 'codes': raw_codes})


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def confirm_recovery_codes_setup(request: Request):
    """Commit the cached recovery codes to Keycloak, replacing any existing
    recovery-codes credential. This is the point at which the user's previously
    saved codes (if any) are invalidated.
    """
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauth_response := require_recent_mfa_auth_if_totp_set(request):
        return reauth_response

    pending_setup = cache.get(make_pending_recovery_codes_cache_key(request.user.pk))
    if not pending_setup or not pending_setup.get('codes'):
        return Response(
            {'success': False, 'error': _('The recovery codes setup expired. Please try again.')},
            status=400,
        )

    user_label = request.data.get('label') or _('Recovery codes')
    try:
        recovery_codes_credentials = KeycloakClient().replace_recovery_codes_credential(
            oidc_id=request.user.oidc_id,
            raw_codes=pending_setup['codes'],
            user_label=str(user_label),
        )
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not save your recovery codes.')}, status=502)

    cache.delete(make_pending_recovery_codes_cache_key(request.user.pk))
    return Response(
        {
            'success': True,
            'credentials': serialize_recovery_codes_credentials(recovery_codes_credentials),
        }
    )


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def remove_recovery_codes_credential(request: Request, credential_id: str):
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauthentication_response := require_recent_mfa_auth(request):
        return reauthentication_response

    try:
        credentials = KeycloakClient().get_recovery_codes_credentials(request.user.oidc_id)
        if credential_id not in [credential.get('id') for credential in credentials]:
            return Response({'success': False, 'error': _('Recovery codes not found.')}, status=404)

        KeycloakClient().delete_credential(request.user.oidc_id, credential_id)
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not remove your recovery codes.')}, status=502)

    return Response({'success': True})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([SignUpThrottle])
def sign_up(request: Request):
    """The api endpoint for signing up a new user.

    We create the Keycloak user and attach its uuid to the local Account's user object.
    We only create the local Accounts user object if the Keycloak user object was successfully created.
    """
    # This file is loaded before models are ready, so we import locally here...for now.
    from thunderbird_accounts.authentication.clients import KeycloakClient
    from thunderbird_accounts.authentication.models import AllowListEntry, User
    from thunderbird_accounts.mail.utils import is_address_taken

    data = request.data

    # This email is the recovery / verification email address at this point
    email = data.get('email')

    timezone = data.get('zoneinfo', 'UTC')
    locale = data.get('locale', 'en')

    partial_username = data.get('partialUsername')
    username = f'{partial_username}@{settings.PRIMARY_EMAIL_DOMAIN}'

    generic_email_error = _('You cannot sign-up with that email address.')

    if not email:
        return Response({'error': generic_email_error, 'type': 'no-email'}, status=400)

    if not is_email_in_allow_list(email):
        # Redirect the user to the tbpro waitlist
        return Response(
            {
                'error': _('You are not on the allow list.'),
                'type': 'go-to-wait-list',
                'href': f'{settings.TB_PRO_WAIT_LIST_URL}?email={quote(email)}',
            },
            status=403,
        )

    # Make sure there's no email alias with this address
    if is_address_taken(username) or is_email_reserved(username):
        return Response({'error': generic_email_error, 'type': 'username-in-use'}, status=400)

    if not data.get('password'):
        return Response(
            {'error': _("You need to enter a password to sign-up."), 'type': 'password-is-empty'},
            status=400,
        )

    # Email gets updated in the middleware's update_user function
    # So we also save it to the recovery_email field here
    # src/thunderbird_accounts/authentication/middleware.py#L126
    user = User(
        username=username,
        email=email,
        recovery_email=email,
        display_name=username,
        language=locale,
        timezone=timezone,
    )

    # Create the user on keycloak's end
    keycloak = KeycloakClient()
    try:
        keycloak_pkid = keycloak.import_user(
            username,
            email,
            timezone,
            password=data.get('password'),
            send_action_email=KeycloakRequiredAction.VERIFY_EMAIL,
            verified_email=False,
        )

        # Save the oidc id so it matches on login
        user.oidc_id = keycloak_pkid
        user.save()

        # Tie the allow list entry with our new user
        if settings.USE_ALLOW_LIST:
            allow_list_entry = AllowListEntry.objects.get(email=email)
            allow_list_entry.user = user
            allow_list_entry.save()
    except (ValueError, InvalidDomainError, AllowListEntry.DoesNotExist):
        # Only username errors raise ValueErrors right now
        return Response(
            {
                'error': generic_email_error,
                'type': 'invalid-domain',
            },
            status=400,
        )
    except ImportUserError as ex:
        sentry_sdk.capture_exception(ex)
        return Response(
            {
                'error': ex.error_desc if ex.error_desc else _('There was an unknown error, please try again later.'),
                'type': ex.error_code if ex.error_code else 'unknown-error',
            },
            status=400 if ex.error_code else 500,
        )

    return Response({'success': True})
