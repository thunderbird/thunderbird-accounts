import base64
import logging
from enum import StrEnum

import requests
from django.conf import settings
from django.utils.crypto import get_random_string

from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError, StalwartError


class StalwartErrors(StrEnum):
    """Errors defined in Stalwart's management api
    https://github.com/stalwartlabs/stalwart/blob/4d819a1041b0adfce3757df50929764afa10e27b/crates/http/src/management/mod.rs#L58
    """

    FIELD_ALREADY_EXISTS = 'fieldAlreadyExists'
    FIELD_MISSING = 'fieldMissing'
    NOT_FOUND = 'notFound'
    UNSUPPORTED = 'unsupported'
    ASSERT_FAILED = 'assertFailed'
    OTHER = 'other'


class MailClient:
    """A partial api client for Stalwart
    Docs: https://stalw.art/docs/api/management/endpoints"""

    def __init__(self):
        self.api_url = f'{settings.STALWART_API_URL}/api'
        self.api_auth_string = settings.STALWART_API_AUTH_STRING
        self.api_auth_method = settings.STALWART_API_AUTH_METHOD

        # Sanity check
        assert self.api_auth_method in ['basic', 'bearer']

        self.authorized_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'{self.api_auth_method} {self.api_auth_string}',
        }

    def _raise_for_error(self, response):
        data = response.json()
        error = data.get('error')
        # Only catch 'other' errors here
        if error == StalwartErrors.OTHER.value:
            details_and_reason = ': '.join([data.get('details'), data.get('reason')])
            raise StalwartError(details_and_reason)

    def _get_principal(self, principal_id: str) -> requests.Response:
        """Returns a response for a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints#fetch-principal

        Important: Don't use this directly!
        """
        response = requests.get(f'{self.api_url}/principal/{principal_id}', headers=self.authorized_headers)
        response.raise_for_status()
        self._raise_for_error(response)

        logging.info(f'[MailClient._get_principal({principal_id}]: {response.json()}')

        return response

    def _create_principal(self, principal_data: dict):
        """Returns a response for the creation of a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints#create-principal

        Important: Don't use this directly!
        """
        if not any([principal_data.get('type', principal_data.get('name'))]):
            raise TypeError('Principal object must contain type AND name.')

        principal_data = {
            'quota': 0,
            'secrets': [],
            'emails': [],
            'urls': [],
            'memberOf': [],
            'roles': [],
            'lists': [],
            'members': [],
            'enabledPermissions': [],
            'disabledPermissions': [],
            'externalMembers': [],
            **principal_data,
        }

        response = requests.post(
            f'{self.api_url}/principal/deploy', json=principal_data, headers=self.authorized_headers
        )
        response.raise_for_status()
        self._raise_for_error(response)

        logging.info(f'[MailClient._create_principal({principal_data}]: {response.json()}')

        return response

    def _update_principal(self, principal_id: str, update_data: list[dict]):
        patch_schema = {
            'type': ('set',),
            'name': ('set',),
            'description': ('set',),
            'quota': ('set',),
            'secrets': ('addItem', 'removeItem'),
            'emails': ('addItem', 'removeItem'),
            'urls': ('addItem', 'removeItem'),
            'memberOf': ('addItem', 'removeItem'),
            'roles': ('addItem', 'removeItem'),
            'lists': ('addItem', 'removeItem'),
            'members': ('addItem', 'removeItem'),
            'enabledPermissions': ('addItem', 'removeItem'),
            'disabledPermissions': ('addItem', 'removeItem'),
            'externalMembers': ('addItem', 'removeItem'),
        }

        # TODO: Look into bringing in pydantic to handle schema validation
        for data in update_data:
            allowed_actions = patch_schema.get(data.get('field'))
            if data.get('action') not in allowed_actions:
                raise TypeError(f'{data.get("action")} is not allowed in')

        response = requests.patch(
            f'{self.api_url}/principal/{principal_id}', json=update_data, headers=self.authorized_headers
        )
        response.raise_for_status()
        self._raise_for_error(response)

        logging.info(f'[MailClient._update_principal({update_data}]: {response.json()}')

        return response

    def get_domain(self, domain):
        response = self._get_principal(domain)

        data = response.json()
        error = data.get('error')

        logging.info(f'[MailClient.get_domain({domain}]: {data}')

        if error == StalwartErrors.NOT_FOUND.value:
            raise DomainNotFoundError(domain)

        assert data.get('data', {}).get('type') == 'domain'

        return data

    def create_dkim(self, domain):
        data = {'id': None, 'algorithm': settings.STALWART_DKIM_ALGO, 'domain': domain, 'selector': None}
        response = requests.post(f'{self.api_url}/dkim', json=data, headers=self.authorized_headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f'[MailClient.create_dkim({domain}]: {data}')

        return data.get('data')

    def create_domain(self, domain, description=''):
        data = {
            'type': 'domain',
            'name': domain,
            'description': description,
        }
        response = self._create_principal(data)
        data = response.json()
        logging.info(f'[MailClient.create_domain({domain}]: {data}')

        # Return the pkid
        return data.get('data')

    def create_account(self, email, username, uuid='', app_password=None):
        data = {'type': 'individual', 'name': username, 'description': uuid, 'emails': [email], 'roles': ['user']}
        if app_password:
            data['secrets'] = [app_password]
        response = self._create_principal(data)
        data = response.json()

        # Return the pkid
        return data.get('data')

    def get_account(self, username):
        response = self._get_principal(username)

        data = response.json()
        error = data.get('error')

        if error == StalwartErrors.NOT_FOUND.value:
            raise AccountNotFoundError(username)

        assert data.get('data', {}).get('type') == 'individual'

        # Return the pkid
        return data.get('data')

    def delete_app_password(self, username, secret):
        response = self._update_principal(
            username,
            [{'action': 'removeItem', 'field': 'secrets', 'value': secret}],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[delete_app_password] err: {data}')
            raise RuntimeError(data)

    def save_app_password(self, username, secret):
        response = self._update_principal(
            username,
            [{'action': 'addItem', 'field': 'secrets', 'value': secret}],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[save_app_password] err: {data}')
            raise RuntimeError(data)

    def make_api_key(self, username, password):
        if not settings.IS_DEV:
            raise RuntimeError('You can only make api keys in dev.')

        basic_auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
        self.authorized_headers['Authorization'] = f'Basic {basic_auth}'

        api_key_name = 'tb-accounts-api-key'
        secret = get_random_string(32)
        data = {'type': 'apiKey', 'name': api_key_name, 'secrets': [secret], 'roles': ['admin']}

        response = self._create_principal(data)
        data = response.json()
        if data.get('error'):
            raise StalwartError(data.get('error'))

        response = self._get_principal(api_key_name)
        data = response.json()

        if not data.get('data', {}).get('id'):
            raise RuntimeError("Error calling stalwart's api")

        return base64.b64encode(f'{api_key_name}:{secret}'.encode()).decode()
