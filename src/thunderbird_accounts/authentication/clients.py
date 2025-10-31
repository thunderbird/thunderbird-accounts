import enum
import json
import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
import sentry_sdk
from django.urls import reverse
from requests.exceptions import RequestException

from django.conf import settings
from thunderbird_accounts.authentication.exceptions import (
    InvalidDomainError,
    ImportUserError,
    SendExecuteActionsEmailError,
    UpdateUserError,
    DeleteUserError,
)
from thunderbird_accounts.mail.utils import is_allowed_domain
from thunderbird_accounts.utils.utils import get_absolute_url


class RequestMethods(enum.StrEnum):
    GET = 'get'
    POST = 'post'
    HEAD = 'head'
    OPTIONS = 'options'
    PUT = 'put'
    PATCH = 'patch'
    DELETE = 'delete'


class KeycloakClient:
    access_token: Optional[str] = None

    def __init__(self):
        self.client_id = settings.KEYCLOAK_ADMIN_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_ADMIN_CLIENT_SECRET

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
    ) -> requests.Response:
        """Handles authenticated requests to the keycloak api
        Endpoint should not have a leading slash to prevent urljoin from trimming the base_url.
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
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.access_token}',
            },
        )

        response.raise_for_status()
        return response

    def get_security_credentials(self, oidc_id):
        endpoint = f'users/{oidc_id}/credentials'
        response = self.request(endpoint, RequestMethods.GET)
        return response.json()

    def verify_password(self, username: str, password: str) -> bool:
        """Verify a user's password by attempting to authenticate with Keycloak.
        :param username: The user's username (email)
        :param password: The password to verify
        :return: True if password is correct, False otherwise
        """

        try:
            response = requests.post(
                settings.OIDC_OP_TOKEN_ENDPOINT,
                data={
                    'client_id': settings.OIDC_RP_CLIENT_ID,
                    'client_secret': settings.OIDC_RP_CLIENT_SECRET,
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                },
            )

            # If authentication is successful, we get a 200 with tokens
            return response.status_code == 200
        except Exception:
            return False

    def _shared_clean(self, username):
        if '@' not in username:
            raise ValueError('Username needs to be the Stalwart/Keycloak login email.')
        if not is_allowed_domain(username):
            raise InvalidDomainError(username)

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
            update_data['attributes'] = update_attribute_data

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
        self, username, backup_email, timezone, name: Optional[str] = None, send_reset_password_email: bool = True
    ) -> str:
        """Creates a user and sends them a reset password email.

        :raises ValueError: If the username is not an email.
        :raises InvalidDomainError: If the username contains an email address that isn't part of the allowed domains.
        :raises ImportUserError: If there was an error during the keycloak user creation api request
        :raises SendExecuteActionsEmailError: If the user was successfully created but the reset password email
        request failed"""
        self._shared_clean(username)

        try:
            response = self.request(
                'users',
                RequestMethods.POST,
                json_data={
                    'username': username,
                    'email': backup_email,
                    'emailVerified': True,
                    'firstName': name,
                    'attributes': {'zoneinfo': timezone, 'locale': 'en'},
                    'enabled': True,
                },
            )
        except RequestException as exc:
            sentry_sdk.capture_exception(exc)
            raise ImportUserError(
                username=username, error=f'Error<{exc.response.status_code}>: {exc.response.content.decode()}'
            )

        # Request returns an empty body on a 201 success, so retrieve pkid from location.
        # ex/ {'Location': 'http://keycloak:8999/admin/realms/tbpro/users/39a7b5e8-7a64-45e3-acf1-ca7d314bfcec', ... }
        response_location = response.headers.get('Location')
        pkid = response_location.split('/')[-1]

        if send_reset_password_email:
            action = 'UPDATE_PASSWORD'
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
