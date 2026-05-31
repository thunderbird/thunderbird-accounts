import json
import requests
import dns.resolver
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, override_settings, TestCase
from thunderbird_accounts.mail.clients import DkimSignatureStage, MailClient, DomainVerificationErrors
from thunderbird_accounts.mail.exceptions import FailedToCreateDKIM


@override_settings(
    STALWART_BASE_API_URL='http://stalwart.test',
    STALWART_API_AUTH_STRING='secret',
    STALWART_API_AUTH_METHOD='bearer',
    CONNECTION_INFO={'SMTP': {'HOST': 'mail.test.com'}},
    HOSTED_DKIM_DOMAIN='dkim.test.net',
    HOSTED_DKIM_SELECTORS=['tm1', 'tm2'],
)
class TestMailClientCheckDomainDNS(SimpleTestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'
        self.expected_host = 'mail.test.com'

    def _mx_record(self, host=None, preference=10):
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = f'{host or self.expected_host}.'
        mock_mx.preference = preference
        return mock_mx

    def _txt_record(self, content):
        mock_txt = MagicMock()
        mock_txt.strings = [content.encode('utf-8')]
        return mock_txt

    def _cname_record(self, target):
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = target
        return mock_cname

    def _resolve_side_effect(
        self,
        *,
        cust_domain=None,
        mx_host=None,
        mx_exception=None,
        spf_content='v=spf1 include:spf.test.com -all',
        dkim_targets=None,
    ):
        cust_domain = cust_domain or self.domain
        if dkim_targets is None:
            dkim_targets = {
                'tm1': f'tm1.{cust_domain}.dkim.test.net.',
                'tm2': f'tm2.{cust_domain}.dkim.test.net.',
            }

        def resolve_side_effect(name, record_type):
            query_name = name.rstrip('.')
            if record_type == 'MX':
                if mx_exception:
                    raise mx_exception
                return [self._mx_record(mx_host)]
            if record_type == 'TXT' and query_name == cust_domain:
                if spf_content is None:
                    raise dns.resolver.NoAnswer()
                return [self._txt_record(spf_content)]
            if record_type == 'CNAME' and '._domainkey.' in query_name:
                selector = query_name.split('._domainkey.')[0]
                if selector not in dkim_targets:
                    raise dns.resolver.NoAnswer()
                return [self._cname_record(dkim_targets[selector])]
            raise dns.resolver.NoAnswer()

        return resolve_side_effect

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_success(self, mock_resolve):
        mock_resolve.side_effect = self._resolve_side_effect()

        result = self.mail_client.check_domain_dns(self.domain)

        self.assertTrue(result['is_verified'])
        self.assertEqual(result['critical_errors'], [])
        self.assertEqual(result['warnings'], [])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_mx_failure(self, mock_resolve):
        mock_resolve.side_effect = self._resolve_side_effect(mx_host='wrong.host.com')

        result = self.mail_client.check_domain_dns(self.domain)

        self.assertFalse(result['is_verified'])
        self.assertIn(DomainVerificationErrors.MX_LOOKUP_ERROR, result['critical_errors'])

        mx_record = next(record for record in result['dns_records'] if record['type'] == 'MX')
        self.assertEqual(mx_record['status'], 'conflict')
        self.assertEqual(mx_record['existing_values'], ['10 wrong.host.com'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_mx_lookup_failure(self, mock_resolve):
        mock_resolve.side_effect = self._resolve_side_effect(mx_exception=dns.resolver.NoAnswer())

        result = self.mail_client.check_domain_dns(self.domain)

        self.assertFalse(result['is_verified'])
        self.assertIn(DomainVerificationErrors.MX_LOOKUP_ERROR, result['critical_errors'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_spf_failure(self, mock_resolve):
        mock_resolve.side_effect = self._resolve_side_effect(spf_content='v=spf1 include:other.com -all')

        result = self.mail_client.check_domain_dns(self.domain)

        self.assertTrue(result['is_verified'])
        self.assertEqual(result['critical_errors'], [])
        self.assertIn(DomainVerificationErrors.SPF_RECORD_NOT_FOUND, result['warnings'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_dkim_failure(self, mock_resolve):
        mock_resolve.side_effect = self._resolve_side_effect(
            dkim_targets={
                'tm1': 'wrong.example.net.',
                'tm2': 'tm2.example.com.dkim.test.net.',
            }
        )

        result = self.mail_client.check_domain_dns(self.domain)

        self.assertTrue(result['is_verified'])
        self.assertEqual(result['critical_errors'], [])
        self.assertIn(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND, result['warnings'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_dkim_missing(self, mock_resolve):
        mock_resolve.side_effect = self._resolve_side_effect(dkim_targets={})

        result = self.mail_client.check_domain_dns(self.domain)

        self.assertTrue(result['is_verified'])
        self.assertEqual(result['critical_errors'], [])
        self.assertIn(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND, result['warnings'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_queries_subdomain_mx(self, mock_resolve):
        cust_domain = 'tb.stosberg.com'
        mock_resolve.side_effect = self._resolve_side_effect(cust_domain=cust_domain)

        result = self.mail_client.check_domain_dns(cust_domain)

        self.assertTrue(result['is_verified'])
        dns_queries = [call_args.args for call_args in mock_resolve.call_args_list]
        self.assertIn((cust_domain, 'MX'), dns_queries)
        self.assertNotIn(('stosberg.com', 'MX'), dns_queries)


class TestMailClientCreateDkim(TestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'
        self.expected_host = 'mail.test.com'

    @override_settings(
        STALWART_DKIM_ALGOS=['Ed25519', 'Rsa'],
        STALWART_DKIM_ALGO_SELECTORS={'Rsa': 'tm1', 'Ed25519': 'tm2'},
        STALWART_DKIM_STAGE_MANAGEMENT_ENABLED=True,
    )
    @patch('requests.post')
    def test_success(self, requests_mock: MagicMock):
        success_response = requests.Response()
        success_response.status_code = 200
        success_response._content = b'{"data": {}}'

        requests_mock.return_value = success_response

        response_data = self.mail_client.create_dkim(self.domain)

        self.assertIsNotNone(response_data)
        self.assertEqual(2, requests_mock.call_count)
        self.assertEqual(
            [
                {
                    'id': None,
                    'algorithm': 'Ed25519',
                    'domain': self.domain,
                    'selector': 'tm2',
                    'stage': DkimSignatureStage.PENDING.value,
                },
                {
                    'id': None,
                    'algorithm': 'Rsa',
                    'domain': self.domain,
                    'selector': 'tm1',
                    'stage': DkimSignatureStage.PENDING.value,
                },
            ],
            [call_args.kwargs['json'] for call_args in requests_mock.call_args_list],
        )

    @override_settings(
        STALWART_DKIM_ALGOS=['Ed25519'],
        STALWART_DKIM_ALGO_SELECTORS={'Ed25519': 'tm2'},
    )
    @patch('requests.post')
    def test_failure_raises_failed_to_create_dkim(self, requests_mock: MagicMock):
        failure_response = requests.Response()
        failure_response.status_code = 500
        failure_response.reason = 'Internal Server Error'

        requests_mock.return_value = failure_response

        with self.assertRaises(FailedToCreateDKIM) as cm:
            self.mail_client.create_dkim(self.domain)

        self.assertEqual('Ed25519', cm.exception.algorithm)
        self.assertEqual(self.domain, cm.exception.domain)
        self.assertIsInstance(cm.exception.__cause__, requests.RequestException)


@override_settings(
    STALWART_DKIM_ALGOS=['Ed25519', 'Rsa'],
    STALWART_DKIM_ALGO_SELECTORS={'Rsa': 'tm1', 'Ed25519': 'tm2'},
)
class TestMailClientEnsureDkim(TestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'

    @patch.object(MailClient, 'create_dkim')
    @patch.object(MailClient, 'get_dkim_dns_records')
    def test_creates_only_missing_selectors(self, mock_get_dkim_dns_records, mock_create_dkim):
        mock_get_dkim_dns_records.return_value = [
            {'type': 'TXT', 'name': 'tm1._domainkey.example.com.', 'content': 'v=DKIM1; p=rsa'},
        ]

        self.mail_client.ensure_dkim(self.domain)

        mock_create_dkim.assert_called_once_with(
            self.domain,
            stage=DkimSignatureStage.PENDING,
            algorithms=['Ed25519'],
        )

    @patch.object(MailClient, 'create_dkim')
    @patch.object(MailClient, 'get_dkim_dns_records')
    def test_does_not_create_when_selectors_exist(self, mock_get_dkim_dns_records, mock_create_dkim):
        mock_get_dkim_dns_records.return_value = [
            {'type': 'TXT', 'name': 'tm1._domainkey.example.com.', 'content': 'v=DKIM1; p=rsa'},
            {'type': 'TXT', 'name': 'tm2._domainkey.example.com.', 'content': 'v=DKIM1; p=ed25519'},
        ]

        self.mail_client.ensure_dkim(self.domain)

        mock_create_dkim.assert_not_called()


@override_settings(STALWART_DKIM_STAGE_MANAGEMENT_ENABLED=True)
class TestMailClientActivatePendingDkim(TestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'

    @patch.object(MailClient, 'make_jmap_admin_call')
    @patch.object(MailClient, 'get_dkim_signatures')
    def test_activates_pending_signatures(self, mock_get_dkim_signatures, mock_make_jmap_admin_call):
        mock_get_dkim_signatures.return_value = [
            {'id': 'sig-1', 'stage': 'pending'},
            {'id': 'sig-2', 'stage': 'active'},
            {'id': 'sig-3', 'stage': 'pending'},
        ]
        mock_make_jmap_admin_call.return_value = {
            'methodResponses': [
                [
                    'x:DkimSignature/set',
                    {'updated': {'sig-1': None, 'sig-3': None}},
                    'u',
                ]
            ]
        }

        updated = self.mail_client.activate_pending_dkim_signatures(self.domain)

        self.assertEqual(['sig-1', 'sig-3'], updated)
        mock_get_dkim_signatures.assert_called_once_with(self.domain)
        mock_make_jmap_admin_call.assert_called_once_with(
            {
                'using': ['urn:ietf:params:jmap:core', 'urn:stalwart:jmap'],
                'methodCalls': [
                    [
                        'x:DkimSignature/set',
                        {'update': {'sig-1': {'stage': 'active'}, 'sig-3': {'stage': 'active'}}},
                        'u',
                    ],
                ],
            }
        )

    @patch.object(MailClient, 'make_jmap_admin_call')
    @patch.object(MailClient, 'get_dkim_signatures')
    def test_no_pending_signatures_is_noop(self, mock_get_dkim_signatures, mock_make_jmap_admin_call):
        mock_get_dkim_signatures.return_value = [{'id': 'sig-1', 'stage': 'active'}]

        updated = self.mail_client.activate_pending_dkim_signatures(self.domain)

        self.assertEqual([], updated)
        mock_make_jmap_admin_call.assert_not_called()

    @patch.object(MailClient, 'make_jmap_admin_call')
    @patch.object(MailClient, 'get_dkim_signatures')
    def test_raises_when_stalwart_does_not_update_signature(self, mock_get_dkim_signatures, mock_make_jmap_admin_call):
        mock_get_dkim_signatures.return_value = [{'id': 'sig-1', 'stage': 'pending'}]
        mock_make_jmap_admin_call.return_value = {
            'methodResponses': [
                [
                    'x:DkimSignature/set',
                    {'notUpdated': {'sig-1': {'type': 'invalidProperties'}}},
                    'u',
                ]
            ]
        }

        with self.assertRaisesRegex(RuntimeError, 'failed to activate DKIM signatures'):
            self.mail_client.activate_pending_dkim_signatures(self.domain)


class TestMailClientDeleteDkim(TestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'

    @patch('requests.get')
    @patch('requests.post')
    def test_success(self, requests_post_mock: MagicMock, requests_get_mock: MagicMock):
        """The GET and POST should not raise any errors and the function should return not None."""
        success_get_response = requests.Response()
        success_get_response.status_code = 200
        success_get_response._content = bytes(
            json.dumps({'data': {'total': 1, 'items': [{'_id': f'rsa-{self.domain}'}]}}), 'utf-8'
        )

        requests_get_mock.return_value = success_get_response

        success_post_response = requests.Response()
        success_post_response.status_code = 200

        requests_post_mock.return_value = success_post_response

        response_data = self.mail_client.delete_dkim(self.domain)
        self.assertIsNotNone(response_data)

        requests_get_mock.assert_called_once()
        call_args = requests_get_mock.call_args
        self.assertEqual(self.domain, call_args[1].get('params', {}).get('filter'))

        requests_post_mock.assert_called_once()

    @patch('requests.get')
    @patch('requests.post')
    def test_success_not_found(self, requests_post_mock: MagicMock, requests_get_mock: MagicMock):
        """The GET should not raise any errors, the POST should not be called, and the function should return None"""
        success_get_response = requests.Response()
        success_get_response.status_code = 200
        success_get_response._content = bytes(json.dumps({'data': {'total': 0, 'items': []}}), 'utf-8')

        requests_get_mock.return_value = success_get_response

        success_post_response = requests.Response()
        success_post_response.status_code = 200

        requests_post_mock.return_value = success_post_response

        response_data = self.mail_client.delete_dkim(self.domain)
        self.assertIsNone(response_data)

        requests_get_mock.assert_called_once()
        call_args = requests_get_mock.call_args
        self.assertEqual(self.domain, call_args[1].get('params', {}).get('filter'))

        requests_post_mock.assert_not_called()

    @patch('requests.get')
    @patch('requests.post')
    def test_internal_server_error_get(self, requests_post_mock: MagicMock, requests_get_mock: MagicMock):
        """GET raises the 500 error and we should catch it"""
        success_get_response = requests.Response()
        success_get_response.status_code = 500
        success_get_response._content = bytes(json.dumps({'data': {'total': 0, 'items': []}}), 'utf-8')

        requests_get_mock.return_value = success_get_response

        with self.assertRaises(requests.RequestException):
            self.mail_client.delete_dkim(self.domain)

    @patch('requests.get')
    @patch('requests.post')
    def test_internal_server_error(self, requests_post_mock: MagicMock, requests_get_mock: MagicMock):
        """GET calls successfully but the POST raises a 500 error and we should catch it"""
        success_get_response = requests.Response()
        success_get_response.status_code = 200
        success_get_response._content = bytes(
            json.dumps({'data': {'total': 1, 'items': [{'_id': f'rsa-{self.domain}'}]}}), 'utf-8'
        )

        requests_get_mock.return_value = success_get_response

        success_post_response = requests.Response()
        success_post_response.status_code = 500

        requests_post_mock.return_value = success_post_response

        with self.assertRaises(requests.RequestException):
            self.mail_client.delete_dkim(self.domain)


@override_settings(
    STALWART_BASE_API_URL='http://stalwart.test',
    STALWART_API_AUTH_STRING='secret',
    STALWART_API_AUTH_METHOD='bearer',
    CONNECTION_INFO={'SMTP': {'HOST': 'mail.test.com'}},
    HOSTED_DKIM_DOMAIN='dkim.test.net',
    HOSTED_DKIM_SELECTORS=['tm1', 'tm2'],
)
class TestMailClientBuildExpectedDNSRecords(SimpleTestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'

    def test_build_expected_dns_records_includes_dkim_cnames(self):
        records = self.mail_client.build_expected_dns_records(self.domain)

        self.assertEqual(records[0], {'type': 'MX', 'name': '@', 'content': 'mail.test.com.', 'priority': '10'})
        dkim_records = [record for record in records if '_domainkey' in record['name']]
        self.assertEqual(
            dkim_records,
            [
                {
                    'type': 'CNAME',
                    'name': 'tm1._domainkey.example.com.',
                    'content': 'tm1.example.com.dkim.test.net.',
                    'priority': '-',
                },
                {
                    'type': 'CNAME',
                    'name': 'tm2._domainkey.example.com.',
                    'content': 'tm2.example.com.dkim.test.net.',
                    'priority': '-',
                },
            ],
        )

    def test_build_expected_dns_records_uses_subdomain_mx_owner(self):
        records = self.mail_client.build_expected_dns_records('tb.stosberg.com')

        self.assertEqual(
            records[0],
            {'type': 'MX', 'name': 'tb.stosberg.com.', 'content': 'mail.test.com.', 'priority': '10'},
        )
        self.assertIn(
            {
                'type': 'SRV',
                'name': '_jmap._tcp.tb.stosberg.com.',
                'content': '1 443 mail.test.com',
                'priority': '0',
            },
            records,
        )
        self.assertIn(
            {
                'type': 'TXT',
                'name': 'tb.stosberg.com.',
                'content': 'v=spf1 include:spf.test.com -all',
                'priority': '-',
            },
            records,
        )

    def test_build_expected_dns_records_normalizes_customer_domain(self):
        records = self.mail_client.build_expected_dns_records('tb.stosberg.com.')

        self.assertEqual(records[1]['name'], '_jmap._tcp.tb.stosberg.com.')
        self.assertNotIn('..', ''.join(record['name'] for record in records))
        self.assertIn(
            {
                'type': 'TXT',
                'name': '_smtp._tls.tb.stosberg.com.',
                'content': 'v=TLSRPTv1; rua=mailto:postmaster@tb.stosberg.com',
                'priority': '-',
            },
            records,
        )

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_check_domain_dns_includes_dns_record_status(self, mock_resolve):
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = 'wrong.host.com.'
        mock_mx.preference = 10

        def resolve_side_effect(name, record_type):
            if record_type == 'MX':
                return [mock_mx]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        result = self.mail_client.check_domain_dns(self.domain)

        mx_record = next(record for record in result['dns_records'] if record['type'] == 'MX')
        self.assertEqual(mx_record['status'], 'conflict')
        self.assertEqual(mx_record['existing_values'], ['10 wrong.host.com'])
