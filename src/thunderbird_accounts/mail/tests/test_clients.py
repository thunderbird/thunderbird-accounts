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
)
class TestMailClientVerifyDomain(SimpleTestCase):
    def setUp(self):
        self.mail_client = MailClient()
        self.domain = 'example.com'
        self.expected_host = 'mail.test.com'

    @patch('thunderbird_accounts.mail.clients.dns.resolver.resolve')
    @patch.object(MailClient, 'get_dns_records')
    def test_verify_domain_success(self, mock_get_dns_records, mock_resolve):
        """Test successful verification of MX, SPF, and DKIM records."""
        # Setup Stalwart DNS records for DKIM reference
        mock_get_dns_records.return_value = [
            {
                'type': 'TXT',
                'name': 'selector._domainkey.example.com.',
                'content': 'v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA',
            }
        ]

        # Mock DNS responses
        def resolve_side_effect(domain, record_type):
            if record_type == 'MX':
                mock_mx = MagicMock()
                mock_mx.exchange.to_text.return_value = f'{self.expected_host}.'
                return [mock_mx]
            elif record_type == 'TXT':
                mock_txt = MagicMock()
                if domain == self.domain:  # SPF
                    mock_txt.strings = [b'v=spf1 include:spf.test.com -all']
                elif 'selector._domainkey' in domain:  # DKIM
                    mock_txt.strings = [b'v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA']
                return [mock_txt]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        is_verified, critical_errors, warnings = self.mail_client.verify_domain(self.domain)

        self.assertTrue(is_verified)
        self.assertEqual(critical_errors, [])
        self.assertEqual(warnings, [])

    @patch('thunderbird_accounts.mail.clients.dns.resolver.resolve')
    def test_verify_domain_mx_failure(self, mock_resolve):
        """Test verification fails when MX record is missing or incorrect."""
        # Case 1: MX record points to wrong host
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = 'wrong.host.com.'
        mock_resolve.return_value = [mock_mx]

        is_verified, critical_errors, warnings = self.mail_client.verify_domain(self.domain)

        self.assertFalse(is_verified)
        self.assertIn(DomainVerificationErrors.MX_LOOKUP_ERROR, critical_errors)

        # Case 2: MX lookup raises exception
        mock_resolve.side_effect = dns.resolver.NoAnswer()
        is_verified, critical_errors, _warnings = self.mail_client.verify_domain(self.domain)

        self.assertFalse(is_verified)
        self.assertIn(DomainVerificationErrors.MX_LOOKUP_ERROR, critical_errors)

    @patch('thunderbird_accounts.mail.clients.dns.resolver.resolve')
    def test_verify_domain_spf_failure(self, mock_resolve):
        """Test verification warns when SPF record is missing or incorrect."""
        # Fix MX to pass first check
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = f'{self.expected_host}.'

        def resolve_side_effect(domain, record_type):
            if record_type == 'MX':
                return [mock_mx]
            if record_type == 'TXT':
                # SPF missing expected include
                mock_txt = MagicMock()
                mock_txt.strings = [b'v=spf1 include:other.com -all']
                return [mock_txt]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        is_verified, critical_errors, warnings = self.mail_client.verify_domain(self.domain)

        self.assertTrue(is_verified)  # SPF failure is not critical
        self.assertEqual(critical_errors, [])
        self.assertIn(DomainVerificationErrors.SPF_RECORD_NOT_FOUND, warnings)

    @patch('thunderbird_accounts.mail.clients.dns.resolver.resolve')
    @patch.object(MailClient, 'get_dns_records')
    def test_verify_domain_dkim_failure(self, mock_get_dns_records, mock_resolve):
        """Test verification warns when DKIM record is incorrect."""
        mock_get_dns_records.return_value = [
            {'type': 'TXT', 'name': 'selector._domainkey.example.com.', 'content': 'v=DKIM1; k=rsa; p=EXPECTED_KEY'}
        ]

        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = f'{self.expected_host}.'

        def resolve_side_effect(domain, record_type):
            if record_type == 'MX':
                return [mock_mx]
            if record_type == 'TXT':
                if domain == self.domain:
                    mock_spf = MagicMock()
                    mock_spf.strings = [b'v=spf1 include:spf.test.com -all']
                    return [mock_spf]
                # DKIM mismatch
                if 'selector._domainkey' in domain:
                    mock_dkim = MagicMock()
                    mock_dkim.strings = [b'v=DKIM1; k=rsa; p=WRONG_KEY']
                    return [mock_dkim]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        is_verified, critical_errors, warnings = self.mail_client.verify_domain(self.domain)

        self.assertTrue(is_verified)  # DKIM failure is not critical
        self.assertEqual(critical_errors, [])
        self.assertIn(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND, warnings)

    @patch('thunderbird_accounts.mail.clients.dns.resolver.resolve')
    @patch.object(MailClient, 'get_dns_records')
    def test_verify_domain_dkim_missing_in_stalwart(self, mock_get_dns_records, mock_resolve):
        """Test verification when Stalwart doesn't return expected DKIM record."""
        mock_get_dns_records.return_value = []  # No DKIM record from Stalwart

        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = f'{self.expected_host}.'

        def resolve_side_effect(domain, record_type):
            if record_type == 'MX':
                return [mock_mx]
            if record_type == 'TXT':
                if domain == self.domain:
                    mock_spf = MagicMock()
                    mock_spf.strings = [b'v=spf1 include:spf.test.com -all']
                    return [mock_spf]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        is_verified, critical_errors, warnings = self.mail_client.verify_domain(self.domain)

        self.assertTrue(is_verified)
        self.assertEqual(critical_errors, [])
        self.assertIn(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND, warnings)


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

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_get_expected_dns_records_with_status(self, mock_resolve):
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = 'wrong.host.com.'
        mock_mx.preference = 10

        def resolve_side_effect(name, record_type):
            if record_type == 'MX':
                return [mock_mx]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        records = self.mail_client.get_expected_dns_records_with_status(self.domain)

        mx_record = next(record for record in records if record['type'] == 'MX')
        self.assertEqual(mx_record['status'], 'conflict')
        self.assertEqual(mx_record['existing_values'], ['10 wrong.host.com'])
