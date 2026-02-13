import json
import requests
import dns.resolver
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, override_settings, TestCase
from thunderbird_accounts.mail.clients import MailClient, DomainVerificationErrors


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
                    mock_txt.strings = [b'v=spf1 include:spf.mail.test.com -all']
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
                    mock_spf.strings = [b'v=spf1 include:spf.mail.test.com -all']
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
                    mock_spf.strings = [b'v=spf1 include:spf.mail.test.com -all']
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

    @patch('requests.post')
    def test_success(self, requests_mock: MagicMock):
        success_response = requests.Response()
        success_response.status_code = 200
        success_response._content = b'{"data": {}}'

        requests_mock.return_value = success_response

        response_data = self.mail_client.create_dkim(self.domain)

        self.assertIsNotNone(response_data)
        requests_mock.assert_called_once()
        call_args = requests_mock.call_args
        self.assertEqual(self.domain, call_args[1].get('json', {}).get('domain'))


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
