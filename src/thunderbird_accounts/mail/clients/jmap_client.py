from typing import Literal
from thunderbird_accounts.mail.clients.jmap_types import SessionResource, JMapRequest, Invocation, JMapResponse
import enum
import json
import requests


class JMAPClient:
    """The tiniest JMAP client you can imagine.
    Source: https://github.com/fastmail/JMAP-Samples/blob/main/python3/tiny_jmap_library.py"""

    class AUTH_TYPES(enum.Enum):
        BASIC = 0
        BEARER = 1

    def __init__(self, base_url: str, username: str, token: str, auth_type: AUTH_TYPES = AUTH_TYPES.BEARER):
        """Initialize using a base_url, username and bearer token"""
        assert len(base_url) > 0
        assert len(username) > 0
        assert len(token) > 0

        self.base_url = base_url
        self.username = username
        self.token = token
        self.auth_type = auth_type
        self.session: SessionResource | None = None
        self.api_url: str | None = None
        self.account_id: str | None = None
        self.identity_id: str | None = None

    def _authorization_value(self):
        return f'Bearer {self.token}' if self.auth_type == self.AUTH_TYPES.BEARER else f'Basic {self.token}'

    def get_session(self) -> SessionResource:
        """Return the JMAP Session Resource as a Python dict"""
        if self.session:
            return self.session
        r = requests.get(
            f'{self.base_url}/.well-known/jmap',
            headers={
                'Content-Type': 'application/json',
                'Authorization': self._authorization_value(),
            },
            allow_redirects=True,
        )
        r.raise_for_status()
        session: SessionResource = r.json()
        self.session = session
        if not self.session:
            raise RuntimeError('Failed to get session')
        self.api_url = session['apiUrl']
        return session

    def get_account_id(self) -> str:
        """Return the accountId for the account matching self.username"""
        if self.account_id:
            return self.account_id

        session = self.get_session()

        account_id = session['primaryAccounts']['urn:ietf:params:jmap:mail']
        self.account_id = account_id
        return account_id

    def get_identity_id(self) -> str:
        """Return the identityId for an address matching self.username"""
        if self.identity_id:
            return self.identity_id

        identity_res = self._jmap_request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:ietf:params:jmap:submission',
                ],
                methodCalls=[Invocation('Identity/get', {'accountId': self.get_account_id()}, 'i')],
            )
        )

        identity_id = next(
            filter(
                lambda i: i['email'] == self.username,
                identity_res['methodResponses'][0][1]['list'],
            )
        )['id']

        self.identity_id = str(identity_id)
        return self.identity_id

    def _jmap_request(self, request_data: JMapRequest, method: Literal['get', 'post'] = 'post') -> JMapResponse:
        """Make a JMAP POST request to the API, returning the response as a
        Python data structure."""
        if not self.api_url:
            raise RuntimeError('Session not available')

        res = requests.request(
            url=self.api_url,
            method=method,
            headers={
                'Content-Type': 'application/json',
                'Authorization': self._authorization_value(),
            },
            data=json.dumps(request_data),
        )
        res.raise_for_status()
        return res.json()
