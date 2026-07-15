import json
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

import sentry_sdk
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from requests.exceptions import RequestException
from rest_framework.request import Request
from rest_framework.response import Response

from thunderbird_accounts.authentication.clients import KeycloakClient, KeycloakMfaClient
from thunderbird_accounts.authentication.exceptions import (
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
from thunderbird_accounts.authentication.tokens import get_user_access_token


class MfaManagementError(Exception):
    status_code = 400
    message = _('Could not update multi-factor authentication.')


class MfaAccountNotConnectedError(MfaManagementError):
    status_code = 400
    message = _('This account is not connected to Keycloak.')


class MfaLoadMethodsUnavailableError(MfaManagementError):
    status_code = 502
    message = _('Could not load multi-factor authentication methods.')


class MfaStartSetupUnavailableError(MfaManagementError):
    status_code = 502
    message = _('Could not start authenticator app setup.')


class MfaSaveAuthenticatorUnavailableError(MfaManagementError):
    status_code = 502
    message = _('Could not save the authenticator app.')


class MfaRemoveAuthenticatorUnavailableError(MfaManagementError):
    status_code = 502
    message = _('Could not remove the authenticator app.')


class MfaSaveRecoveryCodesUnavailableError(MfaManagementError):
    status_code = 502
    message = _('Could not save your recovery codes.')


class MfaRemoveRecoveryCodesUnavailableError(MfaManagementError):
    status_code = 502
    message = _('Could not remove your recovery codes.')


class MfaSetupExpiredError(MfaManagementError):
    status_code = 400
    message = _('The authenticator setup expired. Please try again.')


class MfaInvalidTotpCodeError(MfaManagementError):
    status_code = 400
    message = _('The one-time code is invalid.')


class MfaAuthenticatorAlreadyConfiguredError(MfaManagementError):
    status_code = 409
    message = _('An authenticator app is already set up. Remove it before setting up a new one.')


class MfaTotpRequiredForRecoveryCodesError(MfaManagementError):
    status_code = 409
    message = _('Set up an authenticator app before generating recovery codes.')


class MfaRecoveryCodesRejectedError(MfaManagementError):
    status_code = 400
    message = _('Could not save your recovery codes.')


class MfaAuthenticatorNotFoundError(MfaManagementError):
    status_code = 404
    message = _('Authenticator app not found.')


class MfaRecoveryCodesNotFoundError(MfaManagementError):
    status_code = 404
    message = _('Recovery codes not found.')


class MfaSessionExpiredResponseRequired(MfaManagementError):
    pass


class MfaReauthenticationRequired(MfaManagementError):
    pass


@dataclass(frozen=True)
class MfaMethodsResult:
    totp_credentials: list[dict]
    recovery_codes_credentials: list[dict]

    def as_response_data(self) -> dict:
        return {
            'authenticatorApp': {
                'set': len(self.totp_credentials) > 0,
                'credentials': serialize_totp_credentials(self.totp_credentials),
            },
            'recoveryCodes': {
                'set': len(self.recovery_codes_credentials) > 0,
                'credentials': serialize_recovery_codes_credentials(self.recovery_codes_credentials),
            },
        }


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
    """Serialize stored recovery-codes credentials without returning plaintext codes."""
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


def mfa_management_error_response(request: Request, exc: MfaManagementError) -> Response:
    if isinstance(exc, MfaReauthenticationRequired):
        return make_mfa_reauthentication_response(request)
    if isinstance(exc, MfaSessionExpiredResponseRequired):
        return mfa_session_expired_response()
    return Response({'success': False, 'error': exc.message}, status=exc.status_code)


class MfaManagementService:
    def __init__(
        self,
        request: Request,
        keycloak: KeycloakClient | None = None,
        provider: KeycloakMfaClient | None = None,
    ):
        self.request = request
        self.keycloak = keycloak or KeycloakClient()
        self.provider = provider or KeycloakMfaClient()

    def get_methods(self) -> MfaMethodsResult:
        oidc_id = self._require_oidc_id()
        try:
            totp_credentials = self.keycloak.get_totp_credentials(oidc_id)
            recovery_codes_credentials = self.keycloak.get_recovery_codes_credentials(oidc_id)
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaLoadMethodsUnavailableError() from exc

        self._require_recent_auth_if_totp_set(totp_credentials=totp_credentials)
        return MfaMethodsResult(totp_credentials, recovery_codes_credentials)

    def start_totp_setup(self) -> dict:
        self._require_oidc_id()
        self._require_recent_auth_if_totp_set()
        user_access_token = self._require_user_access_token()

        try:
            setup = self.provider.start_totp_setup(user_access_token)
        except MfaStepUpRequiredError as exc:
            raise MfaReauthenticationRequired() from exc
        except MfaSessionExpiredError as exc:
            raise MfaSessionExpiredResponseRequired() from exc
        except MfaCredentialError as exc:
            # The provider should not reject a (read-only) setup with a client error, but if it
            # does, map it explicitly so it surfaces as a 4xx rather than escaping as a 500.
            if exc.error_code == MFA_REST_ERROR_ALREADY_CONFIGURED:
                raise MfaAuthenticatorAlreadyConfiguredError() from exc
            raise MfaStartSetupUnavailableError() from exc
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaStartSetupUnavailableError() from exc

        cache.set(
            make_pending_totp_cache_key(self.request.user.pk),
            {'secret': setup['secret']},
            settings.MFA_SETUP_CACHE_TTL,
        )

        return {
            'secret': setup.get('encodedSecret'),
            'otpAuthUri': setup.get('otpAuthUri'),
            'issuer': settings.MFA_TOTP_ISSUER,
            'accountName': self.request.user.username,
            'digits': setup.get('digits'),
            'period': setup.get('period'),
            'algorithm': setup.get('algorithm'),
        }

    def confirm_totp_setup(self, code: str, user_label: str, logout_other_sessions: bool = False) -> dict:
        oidc_id = self._require_oidc_id()
        self._require_recent_auth_if_totp_set()
        user_access_token = self._require_user_access_token()
        pending_setup = cache.get(make_pending_totp_cache_key(self.request.user.pk))
        if not pending_setup:
            raise MfaSetupExpiredError()

        try:
            self.provider.register_totp_credential(
                user_access_token=user_access_token,
                secret=pending_setup['secret'],
                code=code,
                user_label=user_label,
            )
        except MfaStepUpRequiredError as exc:
            raise MfaReauthenticationRequired() from exc
        except MfaSessionExpiredError as exc:
            raise MfaSessionExpiredResponseRequired() from exc
        except MfaCredentialError as exc:
            if exc.error_code == MFA_REST_ERROR_ALREADY_CONFIGURED:
                raise MfaAuthenticatorAlreadyConfiguredError() from exc
            raise MfaInvalidTotpCodeError() from exc
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaSaveAuthenticatorUnavailableError() from exc

        if logout_other_sessions:
            self._logout_other_sessions(user_access_token)

        self.request.session[MFA_MANAGEMENT_AUTH_SESSION_KEY] = int(time.time())
        cache.delete(make_pending_totp_cache_key(self.request.user.pk))

        totp_credentials = self._safe_read_credentials(self.keycloak.get_totp_credentials, oidc_id)
        return {'credentials': serialize_totp_credentials(totp_credentials)}

    def remove_totp_credential(self, credential_id: str) -> dict:
        oidc_id = self._require_oidc_id()
        self._require_recent_auth()

        try:
            totp_credentials = self.keycloak.get_totp_credentials(oidc_id)
            if credential_id not in [credential.get('id') for credential in totp_credentials]:
                raise MfaAuthenticatorNotFoundError()

            # Delete the authenticator first, then cascade the orphaned recovery codes. These
            # deletes aren't transactional, so order picks the safe failure mode: a partial
            # failure leaves recovery-codes-only (still loginable) rather than a recovery-less
            # account whose only factor is the authenticator the user likely just lost.
            last_authenticator_removed = len(totp_credentials) == 1
            self.keycloak.delete_credential(oidc_id, credential_id)

            if last_authenticator_removed:
                for recovery_credential in self.keycloak.get_recovery_codes_credentials(oidc_id):
                    self.keycloak.delete_credential(oidc_id, recovery_credential['id'])
        except MfaAuthenticatorNotFoundError:
            raise
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaRemoveAuthenticatorUnavailableError() from exc

        return {'recoveryCodesRemoved': last_authenticator_removed}

    def regenerate_recovery_codes(self, user_label: str) -> dict:
        oidc_id = self._require_oidc_id()
        self._require_recent_auth_if_totp_set()
        user_access_token = self._require_user_access_token()

        try:
            result = self.provider.regenerate_recovery_codes(user_access_token, user_label=user_label)
        except MfaStepUpRequiredError as exc:
            raise MfaReauthenticationRequired() from exc
        except MfaSessionExpiredError as exc:
            raise MfaSessionExpiredResponseRequired() from exc
        except MfaCredentialError as exc:
            if exc.error_code == MFA_REST_ERROR_TOTP_NOT_CONFIGURED:
                raise MfaTotpRequiredForRecoveryCodesError() from exc
            raise MfaRecoveryCodesRejectedError() from exc
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaSaveRecoveryCodesUnavailableError() from exc

        recovery_codes_credentials = self._safe_read_credentials(
            self.keycloak.get_recovery_codes_credentials, oidc_id
        )

        return {
            'codes': result.get('codes', []),
            'credentials': serialize_recovery_codes_credentials(recovery_codes_credentials),
        }

    def remove_recovery_codes_credential(self, credential_id: str) -> dict:
        oidc_id = self._require_oidc_id()
        self._require_recent_auth()

        try:
            credentials = self.keycloak.get_recovery_codes_credentials(oidc_id)
            if credential_id not in [credential.get('id') for credential in credentials]:
                raise MfaRecoveryCodesNotFoundError()

            self.keycloak.delete_credential(oidc_id, credential_id)
        except MfaRecoveryCodesNotFoundError:
            raise
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaRemoveRecoveryCodesUnavailableError() from exc

        return {}

    def _require_oidc_id(self) -> str:
        oidc_id = self.request.user.oidc_id
        if not oidc_id:
            raise MfaAccountNotConnectedError()
        return oidc_id

    def _require_recent_auth(self) -> None:
        if not has_recent_mfa_management_auth(self.request.session):
            raise MfaReauthenticationRequired()

    def _require_recent_auth_if_totp_set(self, totp_credentials: list[dict] | None = None) -> None:
        if has_recent_mfa_management_auth(self.request.session):
            return

        try:
            credentials = (
                totp_credentials
                if totp_credentials is not None
                else self.keycloak.get_totp_credentials(self.request.user.oidc_id)
            )
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise MfaLoadMethodsUnavailableError() from exc

        if credentials:
            raise MfaReauthenticationRequired()

    def _require_user_access_token(self) -> str:
        user_access_token = get_user_access_token(self.request)
        if not user_access_token:
            raise MfaSessionExpiredResponseRequired()
        return user_access_token

    def _safe_read_credentials(self, getter, oidc_id: str) -> list[dict]:
        """Best-effort credential re-read used to echo fresh state back after a mutation.

        The write already succeeded, so a follow-up read failure must not fail the request:
        capture it for observability and return an empty list so the caller still responds 200.
        """
        try:
            return getter(oidc_id)
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            return []

    def _logout_other_sessions(self, user_access_token: str) -> None:
        """Best-effort wrapper: report logout failures to Sentry instead of failing the request."""
        # The TOTP credential is already saved, so a logout failure must not fail the
        # request. Keycloak's Account API preserves the current session (the admin
        # user-logout would evict it too — issue #1005).
        try:
            self.provider.logout_other_sessions(user_access_token)
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
