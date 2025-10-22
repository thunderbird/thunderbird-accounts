import base64
import logging
from enum import StrEnum
from typing import Optional

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
    Docs: https://stalw.art/docs/api/management/endpoints
    Code: https://github.com/stalwartlabs/stalwart/tree/main/crates/http/src/management

    Important note: The principal_id field is principal object's name, not auto-incremented id!
    """

    def __init__(self):
        self.api_url = f'{settings.STALWART_BASE_API_URL}/api'
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

    def _list_principals(self, page=1, limit=100, type: Optional[str] = None) -> requests.Response:
        """Returns a response for a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints/#list-principals

        Important: Don't use this directly!
        """
        params = {'page': page, 'limit': limit}
        if type:
            params['type'] = type

        response = requests.get(
            f'{self.api_url}/principal', params=params, headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        # Reduce log spam
        # logging.info(f'[MailClient._list_principals()]: {response.json()}')

        return response

    def _get_principal(self, principal_id: str) -> requests.Response:
        """Returns a response for a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints#fetch-principal

        Important: Don't use this directly!
        """
        response = requests.get(
            f'{self.api_url}/principal/{principal_id}', headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        logging.info(f'[MailClient._get_principal({principal_id}]: {response.json()}')

        return response

    def _delete_principal(self, principal_id: str) -> requests.Response:
        """Deletes a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints/#delete-principal

        Important: Don't use this directly!
        """
        response = requests.delete(
            f'{self.api_url}/principal/{principal_id}', headers=self.authorized_headers, verify=False
        )
        response.raise_for_status()
        self._raise_for_error(response)

        logging.info(f'[MailClient._delete_principal({principal_id}]: {response.json()}')

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
            f'{self.api_url}/principal/deploy', json=principal_data, headers=self.authorized_headers, verify=False
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
            f'{self.api_url}/principal/{principal_id}', json=update_data, headers=self.authorized_headers, verify=False
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
        response = requests.post(f'{self.api_url}/dkim', json=data, headers=self.authorized_headers, verify=False)
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

    def create_account(
        self, emails: list[str], principal_id: str, full_name: Optional[str] = None, app_password: Optional[str] = None
    ):
        data = {
            'type': 'individual',
            'name': principal_id,
            'description': full_name,
            'emails': emails,
            'roles': ['user'],
        }
        if app_password:
            data['secrets'] = [app_password]
        response = self._create_principal(data)
        data = response.json()

        # Return the pkid
        return data.get('data')

    def get_account(self, principal_id: str) -> dict:
        response = self._get_principal(principal_id)

        data = response.json()
        error = data.get('error')

        if error == StalwartErrors.NOT_FOUND.value:
            raise AccountNotFoundError(principal_id)

        assert data.get('data', {}).get('type') == 'individual'

        # Return the pkid
        return data.get('data')

    def delete_account(self, principal_id: str):
        """Deletes a Stalwart principal object from the given principal_id"""
        return self._delete_principal(principal_id)

    def delete_app_password(self, principal_id: str, secret: str):
        response = self._update_principal(
            principal_id,
            [{'action': 'removeItem', 'field': 'secrets', 'value': secret}],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[delete_app_password] err: {data}')
            raise RuntimeError(data)

    def save_app_password(self, principal_id: str, secret: str):
        response = self._update_principal(
            principal_id,
            [{'action': 'addItem', 'field': 'secrets', 'value': secret}],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[save_app_password] err: {data}')
            raise RuntimeError(data)

    def save_email_addresses(self, principal_id: str, emails: str | list[str]):
        """Adds a new email address to a stalwart's individual principal by uuid."""

        if isinstance(emails, str):
            emails = [emails]

        response = self._update_principal(
            principal_id,
            [{'action': 'addItem', 'field': 'emails', 'value': email} for email in emails],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[save_email_addresses] err: {data}')
            raise RuntimeError(data)

    def replace_email_addresses(self, principal_id: str, emails: list[tuple[str, str]]):
        """Replaces an email address with a new one from a stalwart's individual principal by uuid."""

        actions = []
        for old_email, email in emails:
            actions.append({'action': 'removeItem', 'field': 'emails', 'value': old_email})
            actions.append({'action': 'addItem', 'field': 'emails', 'value': email})

        response = self._update_principal(principal_id, actions)
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[replace_email_addresses] err: {data}')
            raise RuntimeError(data)

    def delete_email_addresses(self, principal_id: str, emails: str | list[str]):
        """Deletes an address from a stalwart's individual principal by uuid."""

        if isinstance(emails, str):
            emails = [emails]

        response = self._update_principal(
            principal_id,
            [{'action': 'removeItem', 'field': 'emails', 'value': email} for email in emails],
        )
        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[delete_email_addresses] err: {data}')
            raise RuntimeError(data)

    def update_individual(
        self,
        principal_id: str,
        primary_email_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ):
        """Updates Stalwart and changes their primary email address and/or full name"""

        update_data = []
        if primary_email_address:
            update_data.append(
                {'action': 'set', 'field': 'name', 'value': primary_email_address},
            )
        if full_name:
            update_data.append(
                {'action': 'set', 'field': 'description', 'value': full_name},
            )

        if len(update_data) == 0:
            raise ValueError('You must provide at least one field to change.')

        response = self._update_principal(principal_id, update_data)

        # Returns data: null on success...
        data = response.json()
        error = data.get('error')
        # I have no idea what the error is yet
        if error:
            logging.error(f'[update_individual] err: {data}')
            raise RuntimeError(data)

    def make_api_key(self, principal_id, password):
        if not settings.IS_DEV:
            raise RuntimeError('You can only make api keys in dev.')

        basic_auth = base64.b64encode(f'{principal_id}:{password}'.encode()).decode()
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
