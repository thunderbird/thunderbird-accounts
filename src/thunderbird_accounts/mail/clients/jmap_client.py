import enum
import logging
from base64 import b64encode
from typing import Literal
from urllib.parse import urlsplit

import requests
from pydantic import ValidationError

from thunderbird_accounts.mail.exceptions import InvalidJMapResponseError, JMapOriginMismatchError
from thunderbird_accounts.mail.types.jmap import Invocation, JMapRequest, JMapResponse, SessionResource


class JMAPClient:
    """The tiniest JMAP client you can imagine.
    Source: https://github.com/fastmail/JMAP-Samples/blob/main/python3/tiny_jmap_library.py"""

    class AUTH_TYPES(enum.Enum):
        BASIC = 0
        BEARER = 1

    def __init__(
        self,
        base_url: str,
        username: str,
        token: str,
        auth_type: AUTH_TYPES = AUTH_TYPES.BEARER,
        verify_ssl: bool | str = True,
        timeout: float | tuple[float, float] = 30,
    ):
        """Initialize using a base_url, username and bearer token"""
        assert len(base_url) > 0
        assert len(username) > 0
        assert len(token) > 0

        self.base_url = base_url
        self.username = username
        if auth_type == self.AUTH_TYPES.BASIC:
            self.token = b64encode(f'{username}:{token}'.encode()).decode()
        else:
            self.token = token
        self.auth_type = auth_type
        self.session: SessionResource | None = None
        self.api_url: str | None = None
        self.account_id: str | None = None
        self.identity_id: str | None = None
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def _authorization_value(self):
        return f'Bearer {self.token}' if self.auth_type == self.AUTH_TYPES.BEARER else f'Basic {self.token}'

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int | None]:
        parsed = urlsplit(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
            raise ValueError('JMAP apiUrl origin is invalid')
        default_port = 443 if parsed.scheme == 'https' else 80
        return parsed.scheme, parsed.hostname, parsed.port or default_port

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
            # RFC 8620 2.2 defines the session resource as fetched "following any redirects",
            # and Stalwart v0.16 ALWAYS 307s /.well-known/jmap -> /jmap/session with an empty
            # body. With redirects disabled, raise_for_status() is a no-op on 3xx and the empty
            # body reaches .json(), raising an untyped JSONDecodeError before any of this class's
            # error handling runs. Redirects stay enabled here; the destination is still pinned,
            # because the origin check below runs against the resulting session.
            #
            # This does NOT relax request(), where allow_redirects=False is correct: a 307/308
            # replays the POST body (DKIM private keys, app passwords) at the new host.
            allow_redirects=True,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        r.raise_for_status()
        try:
            session = SessionResource.model_validate(r.json())
        except ValidationError as ex:
            raise InvalidJMapResponseError(ex) from ex
        if self._origin(session.api_url) != self._origin(self.base_url):
            raise JMapOriginMismatchError(session.api_url, self.base_url)
        self.session = session
        if not self.session:
            raise RuntimeError('Failed to get session')
        self.api_url = session.api_url
        return session

    def get_account_id(self) -> str:
        """Return the accountId for the account matching self.username"""
        if self.account_id:
            return self.account_id

        session = self.get_session()

        account_id = session.primary_accounts['urn:ietf:params:jmap:mail']
        self.account_id = account_id
        return account_id

    def get_identity_id(self) -> str:
        """Return the identityId for an address matching self.username"""
        if self.identity_id:
            return self.identity_id

        identity_res = self.request(
            JMapRequest(
                using=[
                    'urn:ietf:params:jmap:core',
                    'urn:ietf:params:jmap:submission',
                ],
                method_calls=[
                    Invocation(name='Identity/get', arguments={'accountId': self.get_account_id()}, method_call_id='i')
                ],
            )
        )

        identity_id = next(
            filter(
                lambda i: i['email'] == self.username,
                identity_res.method_responses[0].arguments.get('list', []),
            )
        )['id']

        self.identity_id = str(identity_id)
        return self.identity_id

    def request(self, request_data: JMapRequest, method: Literal['get', 'post'] = 'post') -> JMapResponse:
        """Make a JMAP POST request to the API, returning the response as a
        Python data structure."""
        if not self.api_url:
            raise RuntimeError('Session not available')
        logging.debug('[jmap_client.request] sending request')
        res = requests.request(
            url=self.api_url,
            method=method,
            headers={
                'Content-Type': 'application/json',
                'Authorization': self._authorization_value(),
            },
            data=request_data.model_dump_json(exclude_none=True),
            allow_redirects=False,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        res.raise_for_status()
        logging.debug('[jmap_client.request] received response')
        try:
            return JMapResponse.model_validate(res.json())
        except ValidationError as ex:
            raise InvalidJMapResponseError(ex) from ex
