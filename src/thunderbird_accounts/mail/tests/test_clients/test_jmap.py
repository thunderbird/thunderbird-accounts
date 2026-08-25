import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase, override_settings

from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.exceptions import JMapOriginMismatchError, StalwartError
from thunderbird_accounts.mail.clients.mail_client_jmap import MailClientAdminJMAP, MailClientUserJMAP
from thunderbird_accounts.mail.exceptions import AppPasswordSetError
from thunderbird_accounts.mail.tests.test_clients.test_legacy import (
    TestMailClientCheckDomainDNS,
)
from thunderbird_accounts.mail.exceptions import InvalidJMapResponseError
from thunderbird_accounts.mail.types.jmap import Invocation, JMapRequest, JMapResponse, SessionResource
from thunderbird_accounts.mail.types import stalwart


class TestJMAPClientTransport(SimpleTestCase):
    def setUp(self):
        fixture_path = Path(__file__).parent.parent / 'fixtures' / 'jmap_get_session.json'
        with open(fixture_path, 'r') as fh:
            self.session_data = json.load(fh)

    def _response(self, data: object) -> MagicMock:
        response = MagicMock()
        response.json.return_value = data
        return response

    def _request_data(self, secret: str = 'not-sensitive') -> JMapRequest:
        return JMapRequest(
            using=['urn:ietf:params:jmap:core'],
            method_calls=[
                Invocation(name='Secret/set', arguments={'secret': secret}, method_call_id='0'),
            ],
        )

    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.request')
    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.get')
    def test_uses_configured_tls_verification_and_timeout(self, get_mock: MagicMock, request_mock: MagicMock):
        get_mock.return_value = self._response(self.session_data)
        request_mock.return_value = self._response(
            {
                'methodResponses': [['Secret/set', {}, '0']],
                'sessionState': 'state',
            }
        )
        client = JMAPClient(
            'https://stalwart.local',
            'admin',
            'token',
            verify_ssl=True,
            timeout=7,
        )

        client.get_session()
        client.request(self._request_data())

        self.assertIs(get_mock.call_args.kwargs['verify'], True)
        self.assertEqual(get_mock.call_args.kwargs['timeout'], 7)
        self.assertIs(request_mock.call_args.kwargs['verify'], True)
        self.assertEqual(request_mock.call_args.kwargs['timeout'], 7)

    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.request')
    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.get')
    def test_api_requests_do_not_follow_redirects(self, get_mock: MagicMock, request_mock: MagicMock):
        get_mock.return_value = self._response(self.session_data)
        request_mock.return_value = self._response(
            {
                'methodResponses': [['Secret/set', {}, '0']],
                'sessionState': 'state',
            }
        )
        client = JMAPClient('https://stalwart.local', 'admin', 'token')

        client.get_session()
        client.request(self._request_data())

        # The session resource is fetched "following any redirects" per RFC 8620 2.2, and
        # Stalwart v0.16 always 307s /.well-known/jmap. The API resource must NOT follow, since
        # a 307/308 replays the POST body at the new host.
        self.assertIs(get_mock.call_args.kwargs['allow_redirects'], True)
        self.assertIs(request_mock.call_args.kwargs['allow_redirects'], False)

    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.get')
    def test_rejects_session_api_url_on_another_origin(self, get_mock: MagicMock):
        self.session_data['apiUrl'] = 'https://attacker.example/jmap'
        get_mock.return_value = self._response(self.session_data)
        client = JMAPClient('https://stalwart.local', 'admin', 'token')

        with self.assertRaisesRegex(JMapOriginMismatchError, 'apiUrl origin'):
            client.get_session()

    @patch('builtins.open')
    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.get')
    def test_get_session_does_not_write_debug_file(self, get_mock: MagicMock, open_mock: MagicMock):
        get_mock.return_value = self._response(self.session_data)
        client = JMAPClient('https://stalwart.local', 'admin', 'token')

        client.get_session()

        open_mock.assert_not_called()

    @patch('thunderbird_accounts.mail.clients.jmap_client.logging.debug')
    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.request')
    def test_request_does_not_log_secrets(self, request_mock: MagicMock, debug_mock: MagicMock):
        request_mock.return_value = self._response(
            {
                'methodResponses': [['Secret/set', {'secret': 'response-secret'}, '0']],
                'sessionState': 'state',
            }
        )
        client = JMAPClient('https://stalwart.local', 'admin', 'token')
        client.api_url = 'https://stalwart.local/jmap'

        client.request(self._request_data(secret='request-secret'))

        logged = ' '.join(str(call) for call in debug_mock.call_args_list)
        self.assertNotIn('request-secret', logged)
        self.assertNotIn('response-secret', logged)

    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.get')
    def test_malformed_session_response_raises_client_error(self, get_mock: MagicMock):
        get_mock.return_value = self._response([])
        client = JMAPClient('https://stalwart.local', 'admin', 'token')

        with self.assertRaises(InvalidJMapResponseError):
            client.get_session()

    @patch('thunderbird_accounts.mail.clients.jmap_client.requests.request')
    def test_malformed_method_response_raises_client_error(self, request_mock: MagicMock):
        request_mock.return_value = self._response([])
        client = JMAPClient('https://stalwart.local', 'admin', 'token')
        client.api_url = 'https://stalwart.local/jmap'

        with self.assertRaises(InvalidJMapResponseError):
            client.request(self._request_data())


class MockJMapClient(JMAPClient):
    def retrieve_fixture(self, fixture_path: Path) -> dict:
        fixture_path = Path(__file__).parent.parent.joinpath(fixture_path)
        with open(fixture_path, 'r') as fh:
            data = json.loads(fh.read())
        return data

    def get_session(self) -> SessionResource:
        if self.session:
            return self.session

        fixture_data = self.retrieve_fixture(Path('fixtures') / 'jmap_get_session.json')
        # Stub only the HTTP fetch; everything after it, including the origin check, must run
        # exactly as it does in production. Previously this reimplemented the assignment, so the
        # ~17 tests built on this double exercised UNPINNED behaviour and CI carried no signal.
        return self._accept_session(SessionResource(**fixture_data))

    def request(self, request_data: JMapRequest, method: Literal['get', 'post'] = 'post') -> JMapResponse:
        raise NotImplementedError('Monkeypatch me!')


def build_admin_client() -> MailClientAdminJMAP:
    """Build a MailClientAdminJMAP that never touches the network.

    ``MailClientAdminJMAP.__init__`` builds a real ``JMAPClient`` and eagerly fetches the session
    resource over HTTP, so patch ``_get_user_client`` for the duration of construction to hand back
    a ``MockJMapClient`` (which reads the session from a fixture) instead.
    """

    def _mock_user_client(self, *args, **kwargs) -> MockJMapClient:
        client = MockJMapClient('https://stalwart.local', 'admin', 'admin')
        client.get_session()
        return client

    with patch.object(MailClientAdminJMAP, '_get_user_client', _mock_user_client):
        return MailClientAdminJMAP()


def v016_dkim_signature(*, stage: str = 'active') -> dict:
    return {
        'auid': None,
        'canonicalization': 'relaxed/relaxed',
        'expire': None,
        'headers': {
            'From': True,
            'To': True,
            'Date': True,
            'Subject': True,
            'Message-ID': True,
        },
        'privateKey': {'secret': '****', '@type': 'Text'},
        'report': True,
        'thirdParty': None,
        'thirdPartyHash': None,
        'domainId': 'domain-1',
        'memberTenantId': None,
        'selector': 'tm2',
        'createdAt': '2026-07-29T22:35:55Z',
        'nextTransitionAt': None,
        'stage': stage,
        '@type': 'Dkim1Ed25519Sha256',
        'publicKey': 'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=',
        'id': 'signature-1',
    }


def build_user_client() -> MailClientUserJMAP:
    def _mock_user_client(self, *args, **kwargs) -> MockJMapClient:
        client = MockJMapClient('https://stalwart.local', 'user@example.org', 'user-token')
        client.get_session()
        return client

    with patch.object(MailClientUserJMAP, '_get_user_client', _mock_user_client):
        return MailClientUserJMAP('user@example.org', 'user-token')


class TestUserAppPasswords(SimpleTestCase):
    def setUp(self):
        self.mail_client = build_user_client()
        self.mail_client.preflight_check = MagicMock()

    @patch('thunderbird_accounts.mail.tests.test_clients.test_jmap.MockJMapClient.request')
    def test_get_app_passwords_returns_user_scoped_credentials(self, request_mock: MagicMock):
        request_mock.return_value = JMapResponse(
            method_responses=[
                Invocation(
                    name='x:AppPassword/get',
                    arguments={
                        'accountId': 'user-account-id',
                        'list': [
                            {
                                'id': 'app-password-id',
                                'description': 'user@example.org',
                                'permissions': {'@type': 'Inherit'},
                                'allowedIps': {},
                            }
                        ],
                    },
                    method_call_id='0',
                )
            ],
            session_state='state',
        )

        app_passwords = self.mail_client.get_app_passwords()

        self.assertEqual(len(app_passwords), 1)
        self.assertEqual(app_passwords[0].id, 'app-password-id')
        self.assertEqual(app_passwords[0].description, 'user@example.org')
        request = request_mock.call_args.args[0]
        self.assertEqual(request.method_calls[0].name, 'x:AppPassword/get')
        self.assertEqual(request.method_calls[0].arguments, {'accountId': self.mail_client.account_id})

    def test_replace_app_password_removes_only_credentials_with_exact_label(self):
        existing = [
            stalwart.AppPassword(
                id='old-id',
                description='user@example.org',
                permissions={'@type': 'Inherit'},
                allowed_ips={},
            ),
            stalwart.AppPassword(
                id='appointment-id',
                description='appointment-caldav-setup-user@example.org',
                permissions={'@type': 'Inherit'},
                allowed_ips={},
            ),
        ]
        created = self.mail_client.SaveAppPasswordReturn(id='new-id', secret='server-generated-password')
        self.mail_client.get_app_passwords = MagicMock(return_value=existing)
        self.mail_client.save_app_password = MagicMock(return_value=created)
        self.mail_client.delete_app_password = MagicMock(return_value=True)

        result = self.mail_client.replace_app_password('user@example.org')

        self.assertEqual(result, created)
        self.mail_client.save_app_password.assert_called_once_with('user@example.org')
        self.mail_client.delete_app_password.assert_called_once_with(['old-id'])

    def test_replace_app_password_removes_new_credential_when_old_deletion_fails(self):
        existing = [
            stalwart.AppPassword(
                id='old-id',
                description='user@example.org',
                permissions={'@type': 'Inherit'},
                allowed_ips={},
            )
        ]
        created = self.mail_client.SaveAppPasswordReturn(id='new-id', secret='server-generated-password')
        deletion_error = AppPasswordSetError('serverFail', 'could not delete old credential', None)
        self.mail_client.get_app_passwords = MagicMock(return_value=existing)
        self.mail_client.save_app_password = MagicMock(return_value=created)
        self.mail_client.delete_app_password = MagicMock(side_effect=[deletion_error, True])

        with self.assertRaises(AppPasswordSetError) as raised:
            self.mail_client.replace_app_password('user@example.org')

        self.assertIs(raised.exception, deletion_error)
        self.assertEqual(
            self.mail_client.delete_app_password.call_args_list,
            [
                call(['old-id']),
                call('new-id'),
            ],
        )


class AliasJMapContract:
    account_id = 'account-id'
    domain_id = 'domain-id'

    def __init__(
        self,
        account_aliases: dict | None = None,
        catch_all_address: str | None = None,
        concurrent_aliases: dict | None = None,
    ):
        self.account_aliases = deepcopy(account_aliases or {})
        self.catch_all_address = catch_all_address
        self.concurrent_aliases = deepcopy(concurrent_aliases)
        self.account_state = 'account-state-1'
        self.alias_updates_locked = False
        self.requests = []

    @contextmanager
    def alias_update_lock(self, principal_id: str):
        self.alias_updates_locked = True
        try:
            yield
        finally:
            self.alias_updates_locked = False
            if self.concurrent_aliases is not None:
                if self.account_aliases:
                    if not any(alias in self.account_aliases.values() for alias in self.concurrent_aliases.values()):
                        next_id = str(max(map(int, self.account_aliases)) + 1)
                        self.account_aliases[next_id] = next(iter(self.concurrent_aliases.values()))
                else:
                    self.account_aliases = deepcopy(self.concurrent_aliases)
                self.concurrent_aliases = None

    def _response(self, *method_responses: Invocation) -> JMapResponse:
        return JMapResponse(method_responses=list(method_responses), session_state='session-state')

    def _account_data(self) -> dict:
        return {
            'id': self.account_id,
            'name': 'user',
            'domainId': self.domain_id,
            'roles': {'@type': 'User'},
            'permissions': {'@type': 'Inherit'},
            'encryptionAtRest': {'@type': 'Disabled'},
            'aliases': deepcopy(self.account_aliases),
        }

    def _domain_data(self) -> dict:
        return {
            'id': self.domain_id,
            'name': 'custom.test',
            'aliases': {},
            'isEnabled': True,
            'createdAt': '2026-08-19T00:00:00Z',
            'certificateManagement': {'@type': 'Manual'},
            'dkimManagement': {'@type': 'Manual'},
            'dnsManagement': {'@type': 'Manual'},
            'dnsZoneFile': '',
            'catchAllAddress': self.catch_all_address,
            'subAddressing': {'@type': 'Enabled'},
            'allowRelaying': False,
        }

    def _apply_account_update(self, arguments: dict) -> JMapResponse:
        if arguments.get('ifInState') != self.account_state:
            if arguments.get('ifInState') is not None:
                return self._response(
                    Invocation(
                        name='error',
                        arguments={'type': 'stateMismatch', 'description': 'Account state changed'},
                        method_call_id='0',
                    )
                )

        patch_data = arguments['update'][self.account_id]
        for path, value in patch_data.items():
            if not path.startswith('aliases/'):
                continue
            alias_id = path.removeprefix('aliases/')
            if value is None:
                self.account_aliases.pop(alias_id, None)
                self.account_aliases = {str(index): alias for index, alias in enumerate(self.account_aliases.values())}
            else:
                self.account_aliases[alias_id] = value

        return self._response(
            Invocation(
                name='x:Account/set',
                arguments={'updated': {self.account_id: None}},
                method_call_id='0',
            )
        )

    def request(self, request_data: JMapRequest, method: Literal['get', 'post'] = 'post') -> JMapResponse:
        self.requests.append(request_data)
        method_names = [call.name for call in request_data.method_calls]

        if method_names == ['x:Account/query', 'x:Account/get']:
            return self._response(
                Invocation(
                    name='x:Account/query',
                    arguments={'ids': [self.account_id], 'total': 1},
                    method_call_id='0',
                ),
                Invocation(
                    name='x:Account/get',
                    arguments={
                        'list': [self._account_data()],
                        'state': self.account_state,
                    },
                    method_call_id='1',
                ),
            )

        if method_names == ['x:Domain/query', 'x:Domain/get']:
            return self._response(
                Invocation(
                    name='x:Domain/query',
                    arguments={'ids': [self.domain_id], 'total': 1},
                    method_call_id='0',
                ),
                Invocation(
                    name='x:Domain/get',
                    arguments={'list': [self._domain_data()]},
                    method_call_id='1',
                ),
            )

        if method_names == ['x:Domain/query']:
            if self.concurrent_aliases is not None and not self.alias_updates_locked:
                self.account_aliases = deepcopy(self.concurrent_aliases)
                self.account_state = 'account-state-2'
                self.concurrent_aliases = None
            return self._response(
                Invocation(
                    name='x:Domain/query',
                    arguments={'ids': [self.domain_id]},
                    method_call_id='0',
                )
            )

        if method_names == ['x:Account/query']:
            return self._response(
                Invocation(
                    name='x:Account/query',
                    arguments={'ids': [self.account_id], 'total': 1},
                    method_call_id='0',
                )
            )

        if method_names == ['x:Account/set']:
            return self._apply_account_update(request_data.method_calls[0].arguments)

        if method_names == ['x:Domain/set']:
            arguments = request_data.method_calls[0].arguments
            self.catch_all_address = arguments['update'][self.domain_id]['catchAllAddress']
            return self._response(
                Invocation(
                    name='x:Domain/set',
                    arguments={'updated': {self.domain_id: None}},
                    method_call_id='0',
                )
            )

        raise AssertionError(f'Unexpected JMAP methods: {method_names}')


class TestEmailAddressUpdates(SimpleTestCase):
    principal_id = 'user@example.test'

    def build_client(self, contract: AliasJMapContract) -> MailClientAdminJMAP:
        client = build_admin_client()
        client.preflight_check = MagicMock()
        client.client.request = contract.request
        client._alias_update_lock = contract.alias_update_lock
        return client

    def test_concurrent_add_does_not_overwrite_an_alias(self):
        concurrent_alias = {'enabled': True, 'name': 'concurrent', 'domainId': 'domain-id'}
        contract = AliasJMapContract(concurrent_aliases={'0': concurrent_alias})
        client = self.build_client(contract)

        client.save_email_addresses(self.principal_id, 'requested@custom.test')

        self.assertEqual(
            {alias['name'] for alias in contract.account_aliases.values()},
            {'requested', 'concurrent'},
        )

    def test_concurrent_delete_does_not_remove_a_different_alias(self):
        victim = {'enabled': True, 'name': 'victim', 'domainId': 'domain-id'}
        survivor = {'enabled': True, 'name': 'survivor', 'domainId': 'domain-id'}
        contract = AliasJMapContract(
            account_aliases={'0': victim, '1': survivor},
            concurrent_aliases={'0': survivor},
        )
        client = self.build_client(contract)

        with patch.object(client, '_get_domains_by_id', return_value=[stalwart.Domain(**contract._domain_data())]):
            client.delete_email_addresses(self.principal_id, 'victim@custom.test')

        self.assertEqual(contract.account_aliases, {'0': survivor})

    def test_catch_all_add_updates_the_domain(self):
        contract = AliasJMapContract()
        client = self.build_client(contract)

        client.save_email_addresses(self.principal_id, '@custom.test')

        self.assertEqual(contract.catch_all_address, self.principal_id)
        self.assertEqual(contract.account_aliases, {})

    def test_catch_all_delete_updates_the_domain(self):
        contract = AliasJMapContract(catch_all_address=self.principal_id)
        client = self.build_client(contract)

        client.delete_email_addresses(self.principal_id, '@custom.test')

        self.assertIsNone(contract.catch_all_address)
        self.assertEqual(contract.account_aliases, {})


class TestAccountOperations(SimpleTestCase):
    def setUp(self):
        self.mail_client = build_admin_client()
        self.mail_client.account_id = 'admin-account'
        self.mail_client.primary_domain_id = 'primary-domain'

    @patch('uuid.uuid4')
    def test_create_account_does_not_duplicate_primary_address_as_alias(self, uuid4_mock: MagicMock):
        uuid4_mock.return_value = 'temp-id'
        self.mail_client._get_domain_ids_by_name = MagicMock(
            return_value={
                'example.org': 'primary-domain',
                'example.com': 'alias-domain',
            }
        )
        self.mail_client.client.request = MagicMock(
            return_value=JMapResponse(
                method_responses=[
                    Invocation(
                        name='x:Account/set',
                        arguments={'created': {'temp-id': {'id': 'account-id'}}},
                        method_call_id='0',
                    )
                ],
                session_state='a',
            )
        )

        account_id = self.mail_client.create_account(
            ['person@example.org', 'person@example.com'],
            'person@example.org',
        )

        self.assertEqual(account_id, 'account-id')
        request = self.mail_client.client.request.call_args.args[0]
        created_account = request.method_calls[0].arguments['create']['temp-id']
        self.assertEqual(
            created_account['aliases'],
            {
                '0': {
                    'enabled': True,
                    'name': 'person',
                    'domainId': 'alias-domain',
                }
            },
        )

    def test_update_quota_uses_property_patch(self):
        self.mail_client.update_account = MagicMock()

        self.mail_client.update_quota('person@example.org', 2048)

        account_update = self.mail_client.update_account.call_args.args[1]
        self.assertEqual(
            account_update.model_dump(exclude_unset=True),
            {'quotas/maxDiskQuota': 2048},
        )

    def test_list_principals_requests_one_page(self):
        self.mail_client.client.request = MagicMock(
            return_value=JMapResponse(
                method_responses=[
                    Invocation(
                        name='x:Account/query',
                        arguments={'ids': ['account-id']},
                        method_call_id='0',
                    ),
                    Invocation(
                        name='x:Account/get',
                        arguments={
                            'list': [
                                {
                                    'id': 'account-id',
                                    'name': 'person',
                                    '@type': 'User',
                                }
                            ]
                        },
                        method_call_id='1',
                    ),
                ],
                session_state='a',
            )
        )

        principals = self.mail_client.list_principals()

        self.assertEqual(principals, [{'id': 'account-id', 'name': 'person', '@type': 'User'}])
        request = self.mail_client.client.request.call_args.args[0]
        self.assertEqual(len(request.method_calls), 2)
        self.assertEqual(
            request.method_calls[0].model_dump(),
            [
                'x:Account/query',
                {
                    'accountId': 'admin-account',
                    'limit': 100,
                    'position': 0,
                    'calculateTotal': False,
                },
                '0',
            ],
        )
        self.assertEqual(
            request.method_calls[1].model_dump(),
            [
                'x:Account/get',
                {
                    'accountId': 'admin-account',
                    '#ids': {'resultOf': '0', 'name': 'x:Account/query', 'path': '/ids'},
                },
                '1',
            ],
        )


@override_settings(
    STALWART_BASE_API_URL='http://stalwart.test',
    STALWART_API_AUTH_STRING='secret',
    STALWART_API_AUTH_METHOD='bearer',
    CONNECTION_INFO={'SMTP': {'HOST': 'mail.test.com'}},
    SPF_HOST='spf.test.com',
    HOSTED_DKIM_DOMAIN='dkim.test.net',
    HOSTED_DKIM_SELECTORS=['tm1', 'tm2'],
)
class TestCheckDomainDNS(TestMailClientCheckDomainDNS):
    def setUp(self):
        self.mail_client = build_admin_client()
        self.domain = 'example.com'
        self.expected_host = 'mail.test.com'


class TestCreateDkim(SimpleTestCase):
    def setUp(self):
        self.mail_client = build_admin_client()
        self.mail_client.preflight_check = MagicMock()
        self.domain = 'example.com'
        self.expected_host = 'mail.test.com'

    @override_settings(
        STALWART_DKIM_ALGOS=['Ed25519', 'Rsa'],
        STALWART_DKIM_ALGO_SELECTORS={'Rsa': 'tm1', 'Ed25519': 'tm2'},
        STALWART_DKIM_STAGE_MANAGEMENT_ENABLED=True,
    )
    @patch('uuid.uuid4')
    @patch('thunderbird_accounts.mail.tests.test_clients.test_jmap.MockJMapClient.request')
    def test_success(self, requests_mock: MagicMock, uuid4_mock: MagicMock):
        temp_id = 'abc123'
        uuid4_mock.return_value = temp_id

        domain_response = stalwart.Domain(
            id='a',
            name=self.domain,
            is_enabled=True,
            aliases={},
            created_at='2026-07-08T20:45:29Z',
            certificate_management={'@type': 'Automatic'},
            dkim_management={'@type': 'Manual'},
            dns_management={'@type': 'Manual'},
            dns_zone_file='',
            sub_addressing={'@type': 'Enabled'},
            allow_relaying=True,
        ).model_dump()

        # I'm lazy, and we don't really need the first method response
        get_domain_response = JMapResponse(
            method_responses=[
                Invocation(name='x:Query/Domain', arguments={'ids': ['a']}, method_call_id='0'),
                Invocation(name='x:Get/Domain', arguments={'list': [domain_response]}, method_call_id='1'),
            ],
            session_state='a',
        )
        create_dkim_response = JMapResponse(
            method_responses=[
                Invocation(
                    name='x:Set/DkimSignature',
                    arguments={
                        'accountId': 'd333333',
                        'created': {temp_id: {'id': 'i3cjmrt2acac'}},
                    },
                    method_call_id='0',
                ),
            ],
            session_state='a',
        )
        requests_mock.side_effect = [get_domain_response, create_dkim_response, create_dkim_response]

        # Requests:
        # 1. get domain
        # 2. set dkim (Ed25519)
        # 3. set dkim (Rsa)
        response_data = self.mail_client.create_dkim(self.domain)

        self.assertIsNotNone(response_data)
        self.assertEqual(3, requests_mock.call_count)


class TestDkimLifecycle(SimpleTestCase):
    def setUp(self):
        self.mail_client = build_admin_client()
        self.mail_client.account_id = 'admin-account'
        self.domain = 'example.com'

    def test_empty_v016_signature_response_returns_empty_list(self):
        self.mail_client.get_domain = MagicMock(return_value=stalwart.Domain(id='domain-1', **self._domain_data()))
        response = JMapResponse(
            method_responses=[
                Invocation(
                    name='x:DkimSignature/query',
                    arguments={
                        'accountId': 'admin-account',
                        'queryState': 'state-1',
                        'canCalculateChanges': True,
                        'position': 0,
                        'ids': [],
                        'total': 0,
                    },
                    method_call_id='0',
                ),
                Invocation(
                    name='x:DkimSignature/get',
                    arguments={
                        'accountId': 'admin-account',
                        'state': 'state-1',
                        'list': [],
                        'notFound': [],
                    },
                    method_call_id='1',
                ),
            ],
            session_state='session-1',
        )

        with patch.object(self.mail_client.client, 'request', return_value=response):
            signatures = self.mail_client.get_dkim_signatures(self.domain)

        self.assertEqual([], signatures)

    @override_settings(
        STALWART_DKIM_ALGOS=['Ed25519'],
        STALWART_DKIM_ALGO_SELECTORS={'Ed25519': 'tm2'},
        STALWART_DKIM_STAGE_MANAGEMENT_ENABLED=False,
    )
    def test_ensure_creates_active_signature_when_stage_management_is_disabled(self):
        self.mail_client._get_dkim_selectors = MagicMock(return_value=set())
        self.mail_client.get_domain = MagicMock(return_value=stalwart.Domain(id='domain-1', **self._domain_data()))
        response = JMapResponse(
            method_responses=[
                Invocation(
                    name='x:DkimSignature/set',
                    arguments={
                        'accountId': 'admin-account',
                        'created': {'temporary-id': {'id': 'signature-1'}},
                    },
                    method_call_id='0',
                ),
            ],
            session_state='session-1',
        )

        with (
            patch('thunderbird_accounts.mail.clients.mail_client_jmap.uuid.uuid4', return_value='temporary-id'),
            patch.object(self.mail_client.client, 'request', return_value=response) as request_mock,
        ):
            created = self.mail_client.ensure_dkim(self.domain)

        create_request = request_mock.call_args.args[0]
        signature = create_request.method_calls[0].arguments['create']['temporary-id']
        self.assertEqual(['signature-1'], created)
        self.assertEqual('active', signature['stage'])

    @override_settings(STALWART_DKIM_STAGE_MANAGEMENT_ENABLED=True)
    def test_activates_pending_v016_signature(self):
        self.mail_client.get_dkim_signatures = MagicMock(
            return_value=[stalwart.DkimSignature(**v016_dkim_signature(stage='pending'))]
        )
        response = JMapResponse(
            method_responses=[
                Invocation(
                    name='x:DkimSignature/set',
                    arguments={
                        'accountId': 'admin-account',
                        'oldState': 'state-1',
                        'newState': 'state-2',
                        'updated': {'signature-1': None},
                    },
                    method_call_id='0',
                ),
            ],
            session_state='session-1',
        )

        with patch.object(self.mail_client.client, 'request', return_value=response) as request_mock:
            updated = self.mail_client.activate_pending_dkim_signatures(self.domain)

        self.assertEqual(['signature-1'], updated)
        request = request_mock.call_args.args[0]
        self.assertEqual('x:DkimSignature/set', request.method_calls[0].name)
        self.assertEqual(
            {
                'accountId': 'admin-account',
                'update': {'signature-1': {'stage': 'active'}},
            },
            request.method_calls[0].arguments,
        )

    @override_settings(STALWART_DKIM_STAGE_MANAGEMENT_ENABLED=True)
    def test_builds_publication_records_from_pending_v016_signature(self):
        self.mail_client.get_dkim_signatures = MagicMock(
            return_value=[stalwart.DkimSignature(**v016_dkim_signature(stage='pending'))]
        )

        records = self.mail_client.get_dkim_dns_records(self.domain)

        self.assertEqual(
            [
                {
                    'type': 'TXT',
                    'name': 'tm2._domainkey.example.com.',
                    'content': ('v=DKIM1; k=ed25519; h=sha256; p=AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8='),
                }
            ],
            records,
        )

    @staticmethod
    def _domain_data() -> dict:
        return {
            'name': 'example.com',
            'isEnabled': True,
            'aliases': {},
            'createdAt': '2026-07-08T20:45:29Z',
            'certificateManagement': {'@type': 'Automatic'},
            'dkimManagement': {'@type': 'Manual'},
            'dnsManagement': {'@type': 'Manual'},
            'dnsZoneFile': '',
            'subAddressing': {'@type': 'Enabled'},
            'allowRelaying': True,
        }


class TestProductionInterfaceParity(SimpleTestCase):
    def setUp(self):
        self.mail_client = build_admin_client()

    def test_get_telemetry_uses_available_jmap_session(self):
        session = self.mail_client.client.get_session()
        self.mail_client.client.get_session = MagicMock(return_value=session)

        self.assertIs(self.mail_client.get_telemetry(), session)
        self.mail_client.client.get_session.assert_called_once_with()

    def test_get_dkim_dns_records_returns_legacy_dictionary_shape(self):
        self.mail_client._get_dkim_dns_records = MagicMock(
            return_value=[
                stalwart.DnsRecord(
                    type='TXT',
                    name='tm1._domainkey.example.com.',
                    content='v=DKIM1; p=public-key',
                )
            ]
        )

        self.assertEqual(
            self.mail_client.get_dkim_dns_records('example.com'),
            [
                {
                    'type': 'TXT',
                    'name': 'tm1._domainkey.example.com.',
                    'content': 'v=DKIM1; p=public-key',
                }
            ],
        )
        self.mail_client._get_dkim_dns_records.assert_called_once_with('example.com')


class TestOriginMismatchIsRecoverable(SimpleTestCase):
    """The origin mismatch must be catchable by the handlers that already degrade gracefully.

    It is the one new failure guaranteed to fire against a Stalwart whose advertised apiUrl has
    not been corrected, so it must not be the one failure that escapes as a 500.
    """

    def test_is_a_stalwart_error(self):
        err = JMapOriginMismatchError('https://public.example/jmap/', 'https://internal.example')
        self.assertIsInstance(err, StalwartError)
        self.assertIsInstance(err, RuntimeError)

    def test_message_names_both_origins(self):
        """An operator reading Sentry must be able to tell which end to fix."""
        err = JMapOriginMismatchError('https://public.example/jmap/', 'https://internal.example')
        self.assertIn('https://public.example/jmap/', str(err))
        self.assertIn('https://internal.example', str(err))
