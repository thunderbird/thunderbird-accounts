import requests
from django.conf import settings

from thunderbird_accounts.mail.exceptions import DomainNotFoundError, AccountNotFoundError


class MailClient:
    """A partial api client for Stalwart
    Docs: https://stalw.art/docs/api/management/endpoints"""

    def __init__(self):
        self.api_url = settings.STALWART_API_URL
        self.api_key = settings.STALWART_API_KEY
        self.authorized_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }

    def _get_principal(self, principal_id: str) -> requests.Response:
        """Returns a response for a principal object from Stalwart

        Docs: https://stalw.art/docs/api/management/endpoints#fetch-principal

        Important: Don't use this directly!
        """
        response = requests.get(f'{self.api_url}/principal/{principal_id}', headers=self.authorized_headers)
        response.raise_for_status()
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
        return response

    def get_domain(self, domain):
        response = self._get_principal(domain)

        data = response.json()
        error = data.get('error')

        if error == 'notFound':
            raise DomainNotFoundError(domain)

        assert data.get('data', {}).get('type') == 'domain'

        return data

    def create_dkim(self, domain):
        data = {'id': None, 'algorithm': settings.STALWART_DKIM_ALGO, 'domain': domain, 'selector': None}
        response = requests.post(f'{self.api_url}/dkim', json=data, headers=self.authorized_headers)
        response.raise_for_status()
        data = response.json()
        return data.get('data')

    def create_domain(self, domain, description=''):
        data = {
            'type': 'domain',
            'name': domain,
            'description': description,
        }
        response = self._create_principal(data)
        data = response.json()

        # Return the pkid
        return data.get('data')

    def create_account(self, email, username, name=''):
        data = {'type': 'individual', 'name': username, 'description': name, 'emails': [email], 'roles': ['user']}
        response = self._create_principal(data)
        data = response.json()

        # Return the pkid
        return data.get('data')

    def get_account(self, username):
        response = self._get_principal(username)

        data = response.json()
        error = data.get('error')

        if error == 'notFound':
            raise AccountNotFoundError(username)

        assert data.get('data', {}).get('type') == 'individual'

        # Return the pkid
        return data.get('data')
