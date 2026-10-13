import enum
import json
import requests

from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.exceptions import JMapOriginMismatchError


class TinyJMAPClient:
    """The tiniest JMAP client you can imagine.
    Source: https://github.com/fastmail/JMAP-Samples/blob/main/python3/tiny_jmap_library.py"""

    class AUTH_TYPES(enum.Enum):
        BASIC = 0
        BEARER = 1

    def __init__(self, hostname, username, token, auth_type=AUTH_TYPES.BEARER, timeout=30):
        """Initialize using a hostname, username and bearer token"""
        assert len(hostname) > 0
        assert len(username) > 0
        assert len(token) > 0

        self.hostname = hostname
        self.username = username
        self.token = token
        self.auth_type = auth_type
        self.timeout = timeout
        self.session = None
        self.api_url = None
        self.account_id = None
        self.identity_id = None

    def _authorization_value(self):
        return f'Bearer {self.token}' if self.auth_type == self.AUTH_TYPES.BEARER else f'Basic {self.token}'

    def get_session(self):
        """Return the JMAP Session Resource as a Python dict"""
        if self.session:
            return self.session
        r = requests.get(
            self.hostname + '/.well-known/jmap',
            headers={
                'Content-Type': 'application/json',
                'Authorization': self._authorization_value(),
            },
            allow_redirects=True,
            timeout=self.timeout,
        )
        r.raise_for_status()
        session = r.json()
        # Validate API URL matches our hostname
        if JMAPClient._origin(session['apiUrl']) != JMAPClient._origin(self.hostname):
            raise JMapOriginMismatchError(session['apiUrl'], self.hostname)
        self.session = session
        self.api_url = session['apiUrl']
        return session

    def get_account_id(self):
        """Return the accountId for the account matching self.username"""
        if self.account_id:
            return self.account_id

        session = self.get_session()

        account_id = session['primaryAccounts']['urn:ietf:params:jmap:mail']
        self.account_id = account_id
        return account_id

    def get_identity_id(self):
        """Return the identityId for an address matching self.username"""
        if self.identity_id:
            return self.identity_id

        identity_res = self.make_jmap_call(
            {
                'using': [
                    'urn:ietf:params:jmap:core',
                    'urn:ietf:params:jmap:submission',
                ],
                'methodCalls': [['Identity/get', {'accountId': self.get_account_id()}, 'i']],
            }
        )

        identity_id = next(
            filter(
                lambda i: i['email'] == self.username,
                identity_res['methodResponses'][0][1]['list'],
            )
        )['id']

        self.identity_id = str(identity_id)
        return self.identity_id

    def make_jmap_call(self, call):
        """Make a JMAP POST request to the API, returning the response as a
        Python data structure."""
        res = requests.post(
            self.api_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': self._authorization_value(),
            },
            data=json.dumps(call),
            # A 307/308 would replay the authenticated body at the new location.
            allow_redirects=False,
            timeout=self.timeout,
        )
        res.raise_for_status()
        if res.is_redirect:
            raise RuntimeError(f'JMAP API answered {res.status_code} redirect to {res.headers.get("Location")}')
        return res.json()
