import json
import time
from enum import StrEnum
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
from thunderbird_accounts.authentication.exceptions import (
    InvalidDomainError,
    ImportUserError,
    MfaCredentialError,
    MfaSessionExpiredError,
    MfaStepUpRequiredError,
)
from thunderbird_accounts.authentication.mfa import (
    MFA_MANAGEMENT_AUTH_SESSION_KEY,
    MFA_REST_ERROR_ALREADY_CONFIGURED,
    MFA_REST_ERROR_TOTP_NOT_CONFIGURED,
    has_recent_mfa_management_auth,
    make_pending_totp_cache_key,
)
from thunderbird_accounts.authentication.utils import (
    is_email_in_allow_list,
    KeycloakRequiredAction,
    is_email_reserved,
    can_register_with_username,
    get_user_by_contact_email,
)
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.authentication.serializers import UserProfileSerializer


class SignUpThrottle(UserRateThrottle):
    scope = 'sign_up'


class CanISignUpThrottle(UserRateThrottle):
    scope = 'can_i_sign_up'


class CanISignUpResponses(StrEnum):
    WAIT_LIST = 'wait-list'
    LOGIN = 'login'
    SIGN_UP = 'sign-up'


class TotpConfirmThrottle(UserRateThrottle):
    scope = 'totp_confirm'


# mozilla-django-oidc stores the user's access token here when OIDC_STORE_ACCESS_TOKEN is on.
OIDC_ACCESS_TOKEN_SESSION_KEY = 'oidc_access_token'


def get_user_access_token(request: Request) -> str | None:
    """The end user's OIDC access token, forwarded to the self-service mfa-rest provider so
    it operates on the token subject (the caller can only manage their own MFA)."""
    return request.session.get(OIDC_ACCESS_TOKEN_SESSION_KEY)


def mfa_session_expired_response() -> Response:
    return Response(
        {'success': False, 'error': _('Your session has expired. Please sign in again.')},
        status=401,
    )


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

    user_access_token = get_user_access_token(request)
    if not user_access_token:
        return mfa_session_expired_response()

    try:
        setup = KeycloakClient().start_totp_setup(user_access_token)
    except MfaSessionExpiredError:
        return mfa_session_expired_response()
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not start authenticator app setup.')}, status=502)

    # Cache the provider-issued raw secret transiently; it's committed in confirm once
    # the user proves possession. Accounts never generates secret material itself.
    cache.set(
        make_pending_totp_cache_key(request.user.pk),
        {'secret': setup['secret']},
        settings.MFA_SETUP_CACHE_TTL,
    )

    return Response(
        {
            'success': True,
            'secret': setup.get('encodedSecret'),
            'otpAuthUri': setup.get('otpAuthUri'),
            'issuer': settings.MFA_TOTP_ISSUER,
            'accountName': request.user.username,
            'digits': setup.get('digits'),
            'period': setup.get('period'),
            'algorithm': setup.get('algorithm'),
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

    user_access_token = get_user_access_token(request)
    if not user_access_token:
        return mfa_session_expired_response()

    code = request.data.get('code', '')
    pending_setup = cache.get(make_pending_totp_cache_key(request.user.pk))
    if not pending_setup:
        return Response(
            {'success': False, 'error': _('The authenticator setup expired. Please try again.')},
            status=400,
        )

    user_label = request.data.get('label') or _('Authenticator app')
    try:
        # The provider validates the code against the secret and registers the
        # credential in one call; an invalid code raises MfaCredentialError.
        # Registration is enrollment-only: the provider rejects it when an
        # authenticator app already exists (re-enrollment is remove, then set up).
        KeycloakClient().register_totp_credential(
            user_access_token=user_access_token,
            secret=pending_setup['secret'],
            code=code,
            user_label=str(user_label),
        )
    except MfaStepUpRequiredError:
        return make_mfa_reauthentication_response(request)
    except MfaSessionExpiredError:
        return mfa_session_expired_response()
    except MfaCredentialError as exc:
        if exc.error_code == MFA_REST_ERROR_ALREADY_CONFIGURED:
            return Response(
                {
                    'success': False,
                    'error': _('An authenticator app is already set up. Remove it before setting up a new one.'),
                },
                status=409,
            )
        return Response({'success': False, 'error': _('The one-time code is invalid.')}, status=400)
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

    try:
        totp_credentials = KeycloakClient().get_totp_credentials(request.user.oidc_id)
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        totp_credentials = []
    return Response({'success': True, 'credentials': serialize_totp_credentials(totp_credentials)})


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def remove_totp_credential(request: Request, credential_id: str):
    """Remove an authenticator-app credential. When it was the last one, any
    recovery-codes credential is removed along with it: recovery codes are strictly a
    backup for the authenticator, and an account whose only second factor is recovery
    codes ends up unprotected once the codes run out (Keycloak silently deletes the
    credential when the last code is spent)."""
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauthentication_response := require_recent_mfa_auth(request):
        return reauthentication_response

    try:
        keycloak = KeycloakClient()
        totp_credentials = keycloak.get_totp_credentials(request.user.oidc_id)
        if credential_id not in [credential.get('id') for credential in totp_credentials]:
            return Response({'success': False, 'error': _('Authenticator app not found.')}, status=404)

        keycloak.delete_credential(request.user.oidc_id, credential_id)

        last_authenticator_removed = len(totp_credentials) == 1
        if last_authenticator_removed:
            for recovery_credential in keycloak.get_recovery_codes_credentials(request.user.oidc_id):
                keycloak.delete_credential(request.user.oidc_id, recovery_credential['id'])
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not remove the authenticator app.')}, status=502)

    return Response({'success': True, 'recoveryCodesRemoved': last_authenticator_removed})


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def regenerate_recovery_codes(request: Request):
    """Generate and immediately commit a fresh set of recovery codes via the provider,
    replacing any existing recovery-codes credential, and return the plaintext codes once.

    There is no separate pending/confirm step: the destructive "this resets your old
    codes" confirmation is handled in the UI before this endpoint is called. Keycloak
    generates and hashes the codes; accounts never sees a stored hash.
    """
    if not request.user.oidc_id:
        return Response({'success': False, 'error': _('This account is not connected to Keycloak.')}, status=400)

    if reauth_response := require_recent_mfa_auth_if_totp_set(request):
        return reauth_response

    user_access_token = get_user_access_token(request)
    if not user_access_token:
        return mfa_session_expired_response()

    user_label = request.data.get('label') or _('Recovery codes')
    try:
        result = KeycloakClient().regenerate_recovery_codes(user_access_token, user_label=str(user_label))
    except MfaStepUpRequiredError:
        # Backstop for the pre-check above: the provider verifies the token's own
        # acr/auth_time claims, so if the two disagree the user is sent through the
        # step-up redirect rather than getting an opaque failure.
        return make_mfa_reauthentication_response(request)
    except MfaSessionExpiredError:
        return mfa_session_expired_response()
    except MfaCredentialError as exc:
        if exc.error_code == MFA_REST_ERROR_TOTP_NOT_CONFIGURED:
            # Recovery codes are a backup for the authenticator app, never a standalone
            # factor — the provider rejects (re)generation without a TOTP credential.
            return Response(
                {'success': False, 'error': _('Set up an authenticator app before generating recovery codes.')},
                status=409,
            )
        return Response({'success': False, 'error': _('Could not save your recovery codes.')}, status=400)
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        return Response({'success': False, 'error': _('Could not save your recovery codes.')}, status=502)

    try:
        recovery_codes_credentials = KeycloakClient().get_recovery_codes_credentials(request.user.oidc_id)
    except RequestException as exc:
        sentry_sdk.capture_exception(exc)
        recovery_codes_credentials = []

    return Response(
        {
            'success': True,
            'codes': result.get('codes', []),
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
@throttle_classes([CanISignUpThrottle])
def can_i_sign_up(request: Request):
    """This is a temporary fix until we switch off Mailchimp automated emails..."""
    email = request.data.get('email')

    go_to = CanISignUpResponses.WAIT_LIST
    if email and not request.user.is_authenticated:
        has_an_account = get_user_by_contact_email(email)
        is_in_allow_list = is_email_in_allow_list(email)

        # Decide where the user should be sent
        if has_an_account:
            go_to = CanISignUpResponses.LOGIN
        elif is_in_allow_list:
            go_to = CanISignUpResponses.SIGN_UP


    return Response({'go_to': go_to})


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

    data = request.data

    # This email is the recovery / verification email address at this point
    email = data.get('email')

    timezone = data.get('zoneinfo') or 'UTC'
    locale = data.get('locale') or 'en'

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
    if not can_register_with_username(partial_username) or is_email_reserved(username):
        return Response({'error': generic_email_error, 'type': 'username-in-use'}, status=400)

    if not data.get('password'):
        return Response(
            {'error': _('You need to enter a password to sign-up.'), 'type': 'password-is-empty'},
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
            timezone=timezone,
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
