import enum
import json
import datetime
from typing import Optional, TypedDict
from urllib.parse import urljoin

import requests
import sentry_sdk
from django.urls import reverse
from requests import JSONDecodeError
from requests.exceptions import RequestException

from django.conf import settings
from thunderbird_accounts.authentication.exceptions import (
    InvalidDomainError,
    ImportUserError,
    MfaCredentialError,
    MfaSessionExpiredError,
    MfaStepUpRequiredError,
    SendExecuteActionsEmailError,
    UpdateUserError,
    DeleteUserError,
    UpdateUserPlanInfoError,
    GetUserError,
)
from thunderbird_accounts.authentication.mfa import (
    KEYCLOAK_OTP_CREDENTIAL_TYPE,
    KEYCLOAK_RECOVERY_CODES_CREDENTIAL_TYPE,
    MFA_REST_ERROR_STEP_UP_REQUIRED,
)
from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import KeycloakRequiredAction
from thunderbird_accounts.mail.utils import is_allowed_domain
from thunderbird_accounts.core.utils import get_absolute_url


class RequestMethods(enum.StrEnum):
    GET = 'get'
    POST = 'post'
    HEAD = 'head'
    OPTIONS = 'options'
    PUT = 'put'
    PATCH = 'patch'
    DELETE = 'delete'


class TotpSetupResponse(TypedDict, total=False):
    secret: str
    encodedSecret: str
    otpAuthUri: str
    digits: int
    period: int
    algorithm: str


class RecoveryCodesResponse(TypedDict, total=False):
    codes: list[str]
    total: int
    remaining: int


class KeycloakClient:
    access_token: Optional[str] = None

    def __init__(self):
        self.client_id = settings.KEYCLOAK_ADMIN_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_ADMIN_CLIENT_SECRET
        self.access_token = None

    def _get_access_token(self):
        response = requests.post(
            settings.KEYCLOAK_ADMIN_TOKEN_ENDPOINT,
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
            },
        )
        response.raise_for_status()
        data = response.json()
        return data['access_token']

    def request(
        self,
        endpoint: str,
        method: RequestMethods = RequestMethods.GET,
        json_data: Optional[dict] = None,
        data: Optional[dict | list | str] = None,
        params: Optional[dict] = None,
        content_type: str = 'application/json',
    ) -> requests.Response:
        """Handles authenticated requests to the keycloak api
        Endpoint should not have a leading slash to prevent urljoin from trimming the admin API base URL.
        :raises RequestException: On non-200 responses. You can access the response object from the exception."""
        if not self.access_token:
            self.access_token = self._get_access_token()

        # TODO: Consider raising a value error instead of fixing
        if endpoint[0] == '/':
            endpoint = endpoint[1:]

        url = urljoin(settings.KEYCLOAK_API_ENDPOINT, endpoint)

        response = requests.request(
            method=method.value,
            url=url,
            params=params,
            json=json_data,
            data=data,
            headers={
                'Accept': 'application/json',
                'Content-Type': content_type,
                'Authorization': f'Bearer {self.access_token}',
            },
        )

        response.raise_for_status()
        return response

    def get_security_credentials(self, oidc_id):
        endpoint = f'users/{oidc_id}/credentials'
        response = self.request(endpoint, RequestMethods.GET)
        return response.json()

    def get_totp_credentials(self, oidc_id: str) -> list[dict]:
        return [
            credential
            for credential in self.get_security_credentials(oidc_id)
            if credential.get('type') == KEYCLOAK_OTP_CREDENTIAL_TYPE
        ]

    def delete_credential(self, oidc_id: str, credential_id: str) -> bool:
        self.request(f'users/{oidc_id}/credentials/{credential_id}', RequestMethods.DELETE)
        return True

    def logout_user_sessions(self, oidc_id: str) -> bool:
        self.request(f'users/{oidc_id}/logout', RequestMethods.POST)
        return True

    def get_recovery_codes_credentials(self, oidc_id: str) -> list[dict]:
        return [
            credential
            for credential in self.get_security_credentials(oidc_id)
            if credential.get('type') == KEYCLOAK_RECOVERY_CODES_CREDENTIAL_TYPE
        ]

    def _shared_clean(self, username):
        if '@' not in username:
            raise ValueError('Username needs to be the Stalwart/Keycloak login email.')
        if not is_allowed_domain(username):
            raise InvalidDomainError(username)

    def get_user(self, oidc_id: str):
        try:
            response = self.request(
                f'users/{oidc_id}',
                RequestMethods.GET,
            )
            response.raise_for_status()
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            if exc.response is not None:
                raise GetUserError(
                    oidc_id=oidc_id, error=f'Error<{exc.response.status_code}>: {exc.response.content.decode()}'
                )

            raise GetUserError(oidc_id=oidc_id, error=f'Error<{exc}>: No response!')
        return response

    def delete_user(self, oidc_id: str):
        """Updates a user on keycloak with the give attributes.

        :raises DeleteUserError: If there was an error during the keycloak user delete api request"""
        try:
            self.request(f'users/{oidc_id}', RequestMethods.DELETE)
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise DeleteUserError(
                oidc_id=oidc_id, error=f'Error<{exc.response.status_code}>: {exc.response.content.decode()}'
            )

        return True

    def update_user_plan_info(
        self,
        oidc_id: str,
        is_subscribed: bool,
        mail_address_count: Optional[int] = None,
        mail_domain_count: Optional[int] = None,
        mail_storage_bytes: Optional[int] = None,
        send_storage_bytes: Optional[int] = None,
    ):
        """Updates a user on keycloak with the give attributes.

        :raises User.DoesNotExist: If the oidc_id is not connected to a user
        :raises User.MultipleObjectsReturned: If multiple users have the same oidc_id (this is bad for many reasons!)
        :raises GetUserError: If there was an error during the keycloak user get api request
        :raises UpdateUserPlanInfoError: If there was an error during the keycloak user update api request"""
        User.objects.get(oidc_id=oidc_id)
        user_data = self.get_user(oidc_id=oidc_id)

        update_data = user_data.json()
        update_data['attributes'] = {
            **update_data.get('attributes', {}),
            **dict(
                filter(
                    lambda x: x[1] is not None,
                    {
                        'is_subscribed': 'yes' if is_subscribed else 'no',
                        'mail_address_count': mail_address_count,
                        'mail_domain_count': mail_domain_count,
                        'mail_storage_bytes': mail_storage_bytes,
                        'send_storage_bytes': send_storage_bytes,
                    }.items(),
                )
            ),
        }

        try:
            self.request(
                f'users/{oidc_id}',
                RequestMethods.PUT,
                json_data=update_data,
            )
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            if exc.response is not None:
                raise UpdateUserPlanInfoError(
                    oidc_id=oidc_id, error=f'Error<{exc.response.status_code}>: {exc.response.content.decode()}'
                )

            raise UpdateUserPlanInfoError(oidc_id=oidc_id, error=f'Error<{exc}>: No response!')

        return True

    def update_user(
        self,
        oidc_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        email_verified: Optional[bool] = None,
        enabled: Optional[bool] = None,
        timezone: Optional[str] = None,
        locale: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ):
        """Updates a user on keycloak with the give attributes.

        :raises ValueError: If the username is not an email.
        :raises InvalidDomainError: If the username contains an email address that isn't part of the allowed domains.
        :raises UpdateUserError: If there was an error during the keycloak user update api request"""
        if username:
            self._shared_clean(username)

        user_data = self.get_user(oidc_id=oidc_id).json()

        update_data = dict(
            filter(
                lambda x: x[1] is not None,
                {
                    'username': username,
                    'email': email,
                    'emailVerified': email_verified,
                    'firstName': first_name,
                    'lastName': last_name,
                    'enabled': enabled,
                }.items(),
            )
        )

        update_attribute_data = dict(
            filter(
                lambda x: x[1] is not None,
                {
                    'zoneinfo': timezone,
                    'locale': locale or 'en',
                }.items(),
            )
        )

        if update_attribute_data:
            update_data['attributes'] = {
                **(user_data.get('attributes') or {}),
                **update_attribute_data,
            }

        # Merge the two dicts together, update data taking precedence over existing data
        update_data = {
            **user_data,
            **update_data,
        }

        try:
            self.request(f'users/{oidc_id}', RequestMethods.PUT, json_data=update_data)
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            if exc.response is not None:
                raise UpdateUserError(
                    username=username, error=f'Error<{exc.response.status_code}>: {exc.response.content.decode()}'
                )

            raise UpdateUserError(username=username, error=f'Error<{exc}>: No response!')

        return True

    def import_user(
        self,
        username,
        backup_email,
        *,
        timezone,
        name: Optional[str] = None,
        password: Optional[str] = None,
        send_action_email: Optional[KeycloakRequiredAction] = None,
        verified_email: bool = True,
    ) -> str:
        """Creates a user and sends them a reset password email.

        :raises ValueError: If the username is not an email.
        :raises InvalidDomainError: If the username contains an email address that isn't part of the allowed domains.
        :raises ImportUserError: If there was an error during the keycloak user creation api request
        :raises SendExecuteActionsEmailError: If the user was successfully created but the reset password email
        request failed"""
        self._shared_clean(username)

        credentials = []
        if password:
            credentials = [{'type': 'password', 'value': password, 'temporary': False}]

        try:
            response = self.request(
                'users',
                RequestMethods.POST,
                json_data={
                    'username': username,
                    'email': backup_email,
                    'emailVerified': verified_email,
                    'firstName': name,
                    'attributes': {'zoneinfo': timezone, 'locale': 'en'},
                    'credentials': credentials,
                    'enabled': True,
                },
            )
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)

            try:
                error_data: dict = json.loads(exc.response.content.decode())
            except (TypeError, JSONDecodeError):
                # Could not determine explicit error information
                error_data = {}

            # Note: status_code == 409 means the user already exists on keycloak which we should have caught before this
            # function call.
            raise ImportUserError(
                username=username,
                error=f'Error<{exc.response.status_code}>: {exc.response.content.decode()}',
                error_code=error_data.get('error', f'status-{exc.response.status_code}'),
                error_desc=error_data.get('error_description', error_data.get('errorMessage')),
            )

        # Request returns an empty body on a 201 success, so retrieve pkid from location.
        # ex/ {'Location': 'http://keycloak:8999/admin/realms/tbpro/users/39a7b5e8-7a64-45e3-acf1-ca7d314bfcec', ... }
        response_location = response.headers.get('Location')
        pkid = response_location.split('/')[-1]

        if send_action_email:
            action = send_action_email.value
            try:
                self.request(
                    f'users/{pkid}/execute-actions-email',
                    RequestMethods.PUT,
                    data=json.dumps([action]),
                    params={
                        # Keycloak api docs don't specify a type, but will 404 is a float is given
                        'lifespan': int(datetime.timedelta(days=3).total_seconds()),
                        'client_id': settings.OIDC_RP_CLIENT_ID,
                        'redirect_uri': get_absolute_url(reverse('login')),
                    },
                )
            except RequestException as exc:
                sentry_sdk.capture_exception(exc)
                raise SendExecuteActionsEmailError(
                    action=action,
                    oidc_id=pkid,  # If we encounter this error we want to make sure we pass this value back !
                    error=(
                        f'Error<{exc.response.status_code}>: Cannot send email due to: {exc.response.content.decode()}'
                    ),
                )

        return pkid


class KeycloakMfaClient:
    """Client for the self-service keycloak-mfa-rest provider.

    These calls use the end user's forwarded OIDC access token and operate on the
    token subject. Keep this separate from the admin API client so the two trust
    boundaries cannot accidentally share auth or endpoint routing.
    """

    def request(
        self,
        endpoint: str,
        user_access_token: str,
        method: RequestMethods = RequestMethods.GET,
        json_data: Optional[dict] = None,
    ) -> requests.Response:
        if endpoint[0] == '/':
            endpoint = endpoint[1:]

        response = requests.request(
            method=method.value,
            url=urljoin(settings.KEYCLOAK_MFA_API_ENDPOINT, endpoint),
            json=json_data,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {user_access_token}',
            },
        )
        response.raise_for_status()
        return response

    def _provider_request(
        self,
        endpoint: str,
        user_access_token: str,
        method: RequestMethods = RequestMethods.GET,
        json_data: Optional[dict] = None,
    ) -> dict:
        """Call the self-service provider and translate its MFA-specific failures."""
        try:
            response = self.request(endpoint, user_access_token, method, json_data=json_data)
        except RequestException as exc:
            http_response = getattr(exc, 'response', None)
            if http_response is not None:
                try:
                    error_code = http_response.json().get('error')
                except (ValueError, JSONDecodeError):
                    error_code = None
                if http_response.status_code == 401:
                    if error_code == MFA_REST_ERROR_STEP_UP_REQUIRED:
                        raise MfaStepUpRequiredError() from exc
                    raise MfaSessionExpiredError() from exc
                if http_response.status_code in (400, 409):
                    raise MfaCredentialError(error_code or 'invalid_request') from exc
            raise
        return response.json()

    def start_totp_setup(self, user_access_token: str) -> TotpSetupResponse:
        """Generate a TOTP secret + otpauth URI for the calling user without writing it."""
        return self._provider_request('totp/setup', user_access_token, RequestMethods.GET)

    def register_totp_credential(
        self,
        user_access_token: str,
        secret: str,
        code: str,
        user_label: str,
    ) -> dict:
        """Verify ``code`` against ``secret`` and register an enrollment-only TOTP credential."""
        return self._provider_request(
            'totp/register',
            user_access_token,
            RequestMethods.POST,
            json_data={
                'secret': secret,
                'code': code,
                'deviceName': user_label,
            },
        )

    def regenerate_recovery_codes(
        self,
        user_access_token: str,
        user_label: Optional[str] = None,
    ) -> RecoveryCodesResponse:
        """Replace recovery codes for the calling user and return the plaintext codes once."""
        json_data = {'deviceName': user_label} if user_label else None
        return self._provider_request(
            'recovery-codes/regenerate',
            user_access_token,
            RequestMethods.POST,
            json_data=json_data,
        )
