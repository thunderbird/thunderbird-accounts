import requests

from thunderbird_accounts import settings


class KeycloakClient:
    def __init__(self):
        self.client_id = settings.KEYCLOAK_ADMIN_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_ADMIN_CLIENT_SECRET
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        response = requests.post(settings.KEYCLOAK_ADMIN_TOKEN_ENDPOINT, data={
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
        })
        response.raise_for_status()
        data = response.json()
        return data['access_token']


    def get_security_credentials(self, oidc_id):
        response = requests.get(
            f'{settings.KEYCLOAK_API_ENDPOINT}/users/{oidc_id}/credentials', headers={
                'Authorization': f'Bearer {self.access_token}',
            })
        response.raise_for_status()
        return response.json()
