from django.test import SimpleTestCase, TestCase
from unittest.mock import MagicMock, patch
import dns.rdatatype
import dns.resolver

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.mail.exceptions import EmailNotValidError
from thunderbird_accounts.mail.clients import DNSRecordStatus, StaleDNSRecordCode
from thunderbird_accounts.mail.utils import (
    check_cname_record_status,
    check_mx_record_status,
    check_srv_record_status,
    check_stale_dns_records,
    check_txt_record_status,
    enrich_dns_records_with_status,
    normalize_dns_query_name,
    validate_email,
)


class ValidateEmailTestCase(TestCase):
    """Tests for validate_email, focused on the local-part length check.

    USERNAME_MIN_LENGTH = 3  →  local parts shorter than 3 chars are rejected
    USERNAME_MAX_LENGTH = 150 →  local parts longer than 150 chars are rejected
    """

    DOMAIN = 'example.com'

    def _email(self, local_part: str) -> str:
        return f'{local_part}@{self.DOMAIN}'

    # ------------------------------------------------------------------
    # Boundary: minimum length
    # ------------------------------------------------------------------

    def test_local_part_at_min_length_is_valid(self):
        """A local part of exactly USERNAME_MIN_LENGTH (3) characters is accepted."""
        local_part = 'a' * User.USERNAME_MIN_LENGTH
        self.assertTrue(validate_email(self._email(local_part)))

    def test_local_part_one_below_min_raises(self):
        """A local part of USERNAME_MIN_LENGTH - 1 (2) characters is rejected."""
        local_part = 'a' * (User.USERNAME_MIN_LENGTH - 1)
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(local_part))

    def test_local_part_single_char_raises(self):
        """A single-character local part is rejected."""
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email('a'))

    def test_empty_local_part_raises(self):
        """An empty local part (length 0) is rejected."""
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(''))

    # ------------------------------------------------------------------
    # Boundary: maximum length
    # ------------------------------------------------------------------

    def test_local_part_at_max_length_is_valid(self):
        """A local part of exactly USERNAME_MAX_LENGTH (150) characters is accepted."""
        local_part = 'a' * User.USERNAME_MAX_LENGTH
        self.assertTrue(validate_email(self._email(local_part)))

    def test_local_part_above_max_raises(self):
        """A local part longer than USERNAME_MAX_LENGTH (150) is rejected."""
        local_part = 'a' * (User.USERNAME_MAX_LENGTH + 1)
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(local_part))

    # ------------------------------------------------------------------
    # Format checks
    # ------------------------------------------------------------------

    def test_missing_at_sign_raises(self):
        """An email without '@' is rejected before the length check."""
        with self.assertRaises(EmailNotValidError):
            validate_email('notanemail')

    def test_invalid_email_format_raises(self):
        """A string with '@' but an otherwise invalid format is rejected."""
        with self.assertRaises(EmailNotValidError):
            validate_email('abc@')

    def test_valid_email_returns_true(self):
        """A well-formed email within length bounds returns True."""
        self.assertTrue(validate_email('validuser@example.com'))

    # ------------------------------------------------------------------
    # Custom error message
    # ------------------------------------------------------------------

    def test_custom_error_message_is_used(self):
        """The caller-supplied error_message is propagated in the exception."""
        custom_msg = 'Custom error for tests'
        local_part = 'a' * (User.USERNAME_MIN_LENGTH - 1)
        with self.assertRaises(EmailNotValidError) as ctx:
            validate_email(self._email(local_part), error_message=custom_msg)
        self.assertEqual(ctx.exception.error_message, custom_msg)

    # ------------------------------------------------------------------
    # min_length override
    # ------------------------------------------------------------------

    def test_min_length_override_allows_short_local_part(self):
        """Callers can lower the minimum below USERNAME_MIN_LENGTH."""
        self.assertTrue(validate_email(self._email('a'), min_length=1))

    def test_min_length_override_still_rejects_below_override(self):
        """The overridden minimum is still enforced."""
        with self.assertRaises(EmailNotValidError):
            validate_email(self._email(''), min_length=1)


class TestNormalizeDNSQueryName(SimpleTestCase):
    def test_at_sign_returns_domain_name(self):
        self.assertEqual(normalize_dns_query_name('@', 'example.com'), 'example.com')

    def test_strips_trailing_dot(self):
        self.assertEqual(normalize_dns_query_name('_dmarc.example.com.', 'example.com'), '_dmarc.example.com')


class TestDNSRecordStatus(SimpleTestCase):
    def setUp(self):
        self.domain = 'example.com'

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_mx_match_with_extra_records(self, mock_resolve):
        mock_correct = MagicMock()
        mock_correct.exchange.to_text.return_value = 'mail.test.com.'
        mock_correct.preference = 10
        mock_extra = MagicMock()
        mock_extra.exchange.to_text.return_value = 'aspmx.l.google.com.'
        mock_extra.preference = 1
        mock_resolve.return_value = [mock_extra, mock_correct]

        status, existing_values = check_mx_record_status(
            self.domain,
            {'type': 'MX', 'name': '@', 'content': 'mail.test.com', 'priority': '10'},
        )

        self.assertEqual(status, DNSRecordStatus.MATCH)
        self.assertEqual(existing_values, [])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_mx_conflict(self, mock_resolve):
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = 'aspmx.l.google.com.'
        mock_mx.preference = 10
        mock_resolve.return_value = [mock_mx]

        status, existing_values = check_mx_record_status(
            self.domain,
            {'type': 'MX', 'name': '@', 'content': 'mail.test.com', 'priority': '10'},
        )

        self.assertEqual(status, DNSRecordStatus.CONFLICT)
        self.assertEqual(existing_values, ['10 aspmx.l.google.com'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_srv_match_with_extra_records(self, mock_resolve):
        mock_correct = MagicMock()
        mock_correct.priority = 0
        mock_correct.weight = 1
        mock_correct.port = 443
        mock_correct.target.to_text.return_value = 'mail.test.com.'
        mock_extra = MagicMock()
        mock_extra.priority = 0
        mock_extra.weight = 1
        mock_extra.port = 443
        mock_extra.target.to_text.return_value = 'other.test.com.'
        mock_resolve.return_value = [mock_extra, mock_correct]

        status, existing_values = check_srv_record_status(
            self.domain,
            {
                'type': 'SRV',
                'name': f'_jmap._tcp.{self.domain}.',
                'content': '1 443 mail.test.com',
                'priority': '0',
            },
        )

        self.assertEqual(status, DNSRecordStatus.MATCH)
        self.assertEqual(existing_values, [])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_cname_match(self, mock_resolve):
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = 'tm1.example.com.dkim.test.net.'
        mock_resolve.return_value = [mock_cname]

        status, existing_values = check_cname_record_status(
            self.domain,
            {
                'type': 'CNAME',
                'name': f'tm1._domainkey.{self.domain}.',
                'content': 'tm1.example.com.dkim.test.net.',
                'priority': '-',
            },
        )

        self.assertEqual(status, DNSRecordStatus.MATCH)
        self.assertEqual(existing_values, [])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_cname_conflict(self, mock_resolve):
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = 'wrong.example.net.'
        mock_resolve.return_value = [mock_cname]

        status, existing_values = check_cname_record_status(
            self.domain,
            {
                'type': 'CNAME',
                'name': f'tm1._domainkey.{self.domain}.',
                'content': 'tm1.example.com.dkim.test.net.',
                'priority': '-',
            },
        )

        self.assertEqual(status, DNSRecordStatus.CONFLICT)
        self.assertEqual(existing_values, ['wrong.example.net'])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_spf_match(self, mock_resolve):
        mock_txt = MagicMock()
        mock_txt.strings = [b'v=spf1 include:spf.test.com -all']
        mock_resolve.return_value = [mock_txt]

        status, existing_values = check_txt_record_status(
            self.domain,
            {
                'type': 'TXT',
                'name': self.domain,
                'content': 'v=spf1 include:spf.test.com -all',
                'priority': '-',
            },
        )

        self.assertEqual(status, DNSRecordStatus.MATCH)
        self.assertEqual(existing_values, [])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_dkim_match_among_multiple_records(self, mock_resolve):
        mock_wrong = MagicMock()
        mock_wrong.strings = [b'v=DKIM1; k=rsa; p=wrongkey']
        mock_correct = MagicMock()
        mock_correct.strings = [b'v=DKIM1; k=rsa; p=expectedkey']
        mock_resolve.return_value = [mock_wrong, mock_correct]

        status, existing_values = check_txt_record_status(
            self.domain,
            {
                'type': 'TXT',
                'name': f'selector._domainkey.{self.domain}.',
                'content': 'v=DKIM1; k=rsa; p=expectedkey',
                'priority': '-',
            },
        )

        self.assertEqual(status, DNSRecordStatus.MATCH)
        self.assertEqual(existing_values, [])

    @patch('thunderbird_accounts.mail.utils.dns.resolver.resolve')
    def test_enrich_dns_records_with_status(self, mock_resolve):
        mock_mx = MagicMock()
        mock_mx.exchange.to_text.return_value = 'aspmx.l.google.com.'
        mock_mx.preference = 10

        def resolve_side_effect(name, record_type):
            if record_type == 'MX':
                return [mock_mx]
            raise dns.resolver.NoAnswer()

        mock_resolve.side_effect = resolve_side_effect

        expected_records = [
            {'type': 'MX', 'name': '@', 'content': 'mail.test.com', 'priority': '10'},
            {
                'type': 'SRV',
                'name': f'_jmap._tcp.{self.domain}.',
                'content': '1 443 mail.test.com',
                'priority': '0',
            },
        ]
        enriched = enrich_dns_records_with_status(self.domain, expected_records)

        self.assertEqual(enriched[0]['status'], DNSRecordStatus.CONFLICT.value)
        self.assertEqual(enriched[0]['existing_values'], ['10 aspmx.l.google.com'])
        self.assertEqual(enriched[1]['status'], DNSRecordStatus.MISSING.value)
        self.assertNotIn('existing_values', enriched[1])


class TestStaleDNSRecords(SimpleTestCase):
    def setUp(self):
        self.domain = 'example.com'

    def _patch_resolver(self, resolve_side_effect):
        """Patch dns.resolver.Resolver so its resolve method uses the given side effect."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = resolve_side_effect
        return patch(
            'thunderbird_accounts.mail.utils.dns.resolver.Resolver',
            return_value=mock_resolver,
        )

    def test_autodiscover_cname_stale(self):
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = 'autodiscover.outlook.com.'

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                return [mock_cname]
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['code'], StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value)
        self.assertEqual(stale_records[0]['type'], 'CNAME')
        self.assertEqual(stale_records[0]['name'], f'autodiscover.{self.domain}')
        self.assertEqual(stale_records[0]['existing_values'], ['autodiscover.outlook.com'])

    def test_autodiscover_cname_stale_even_if_pointing_to_our_host(self):
        """Any autodiscover CNAME is stale — we don't use autodiscover at all."""
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = 'mail.thundermail.com.'

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                return [mock_cname]
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['code'], StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value)

    def test_autodiscover_cname_via_a_lookup_chain(self):
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = 'autodiscover.gogo.com.'

        mock_rrset = MagicMock()
        mock_rrset.rdtype = dns.rdatatype.CNAME
        mock_rrset.__iter__ = MagicMock(return_value=iter([mock_cname]))

        mock_a_answer = MagicMock()
        mock_a_answer.response.answer = [mock_rrset]

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                raise dns.resolver.NoAnswer()
            if record_type == 'A':
                return mock_a_answer
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['existing_values'], ['autodiscover.gogo.com'])

    def test_autodiscover_cname_via_aaaa_lookup_chain(self):
        mock_cname = MagicMock()
        mock_cname.target.to_text.return_value = 'autodiscover.example.net.'

        mock_rrset = MagicMock()
        mock_rrset.rdtype = dns.rdatatype.CNAME
        mock_rrset.__iter__ = MagicMock(return_value=iter([mock_cname]))

        mock_aaaa_answer = MagicMock()
        mock_aaaa_answer.response.answer = [mock_rrset]

        def resolve_side_effect(name, record_type):
            if record_type in {'CNAME', 'A'}:
                raise dns.resolver.NoAnswer()
            if record_type == 'AAAA':
                return mock_aaaa_answer
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['type'], 'CNAME')
        self.assertEqual(stale_records[0]['existing_values'], ['autodiscover.example.net'])

    def test_autodiscover_direct_a_record_stale(self):
        mock_a = MagicMock()
        mock_a.to_text.return_value = '203.0.113.10'

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                raise dns.resolver.NoAnswer()
            if record_type == 'A':
                mock_a_answer = MagicMock()
                mock_a_answer.response.answer = []
                mock_a_answer.__iter__ = MagicMock(return_value=iter([mock_a]))
                return mock_a_answer
            if record_type == 'AAAA':
                raise dns.resolver.NoAnswer()
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['type'], 'A')
        self.assertEqual(stale_records[0]['existing_values'], ['203.0.113.10'])

    def test_autodiscover_direct_a_and_aaaa_records_stale(self):
        mock_a = MagicMock()
        mock_a.to_text.return_value = '203.0.113.10'
        mock_aaaa = MagicMock()
        mock_aaaa.to_text.return_value = '2001:db8::10'

        def make_answer(*records):
            answer = MagicMock()
            answer.response.answer = []
            answer.__iter__ = MagicMock(return_value=iter(records))
            return answer

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                raise dns.resolver.NoAnswer()
            if record_type == 'A':
                return make_answer(mock_a)
            if record_type == 'AAAA':
                return make_answer(mock_aaaa)
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 2)
        self.assertEqual(stale_records[0]['type'], 'A')
        self.assertEqual(stale_records[0]['existing_values'], ['203.0.113.10'])
        self.assertEqual(stale_records[1]['type'], 'AAAA')
        self.assertEqual(stale_records[1]['existing_values'], ['2001:db8::10'])

    def test_autodiscover_srv_stale(self):
        mock_srv = MagicMock()
        mock_srv.priority = 0
        mock_srv.weight = 0
        mock_srv.port = 443
        mock_srv.target.to_text.return_value = 'cpanelemaildiscovery.cpanel.net.'

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                raise dns.resolver.NoAnswer()
            if record_type == 'SRV':
                return [mock_srv]
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['code'], StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value)
        self.assertEqual(stale_records[0]['name'], f'_autodiscover._tcp.{self.domain}')
        self.assertEqual(stale_records[0]['existing_values'], ['0 0 443 cpanelemaildiscovery.cpanel.net'])

    def test_autodiscover_srv_stale_even_if_pointing_to_our_host(self):
        """Any autodiscover SRV is stale — we don't use autodiscover at all."""
        mock_srv = MagicMock()
        mock_srv.priority = 0
        mock_srv.weight = 1
        mock_srv.port = 443
        mock_srv.target.to_text.return_value = 'mail.thundermail.com.'

        def resolve_side_effect(name, record_type):
            if record_type == 'CNAME':
                raise dns.resolver.NoAnswer()
            if record_type == 'SRV':
                return [mock_srv]
            raise dns.resolver.NoAnswer()

        with self._patch_resolver(resolve_side_effect):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(len(stale_records), 1)
        self.assertEqual(stale_records[0]['code'], StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value)

    def test_no_stale_records_when_missing(self):
        with self._patch_resolver(lambda name, rdtype: (_ for _ in ()).throw(dns.resolver.NoAnswer())):
            stale_records = check_stale_dns_records(self.domain)

        self.assertEqual(stale_records, [])
