import base64
from unittest.mock import Mock, call

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from django.test import SimpleTestCase, override_settings

from thunderbird_accounts.mail.dkim import (
    CloudflareDNSClient,
    build_customer_dkim_cname_records,
    build_hosted_dkim_txt_record_names,
    build_hosted_dkim_txt_records,
    delete_hosted_dkim_txt_records,
    dkim_signatures_to_dns_records,
)


def _cloudflare_page(records):
    page = Mock()
    page.result = records
    return page


def _ed25519_public_key():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    expected_public_key = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    return public_pem, expected_public_key


@override_settings(HOSTED_DKIM_DOMAIN='dkim.example.net', HOSTED_DKIM_SELECTORS=['tm1', 'tm2', 'tm3'])
class HostedDkimRecordBuilderTestCase(SimpleTestCase):
    def test_builds_customer_cname_records_for_all_selectors(self):
        records = build_customer_dkim_cname_records('Example.COM.')

        self.assertEqual(
            [
                {
                    'type': 'CNAME',
                    'name': 'tm1._domainkey.example.com.',
                    'content': 'tm1.example.com.dkim.example.net.',
                    'priority': '-',
                },
                {
                    'type': 'CNAME',
                    'name': 'tm2._domainkey.example.com.',
                    'content': 'tm2.example.com.dkim.example.net.',
                    'priority': '-',
                },
                {
                    'type': 'CNAME',
                    'name': 'tm3._domainkey.example.com.',
                    'content': 'tm3.example.com.dkim.example.net.',
                    'priority': '-',
                },
            ],
            records,
        )

    def test_builds_hosted_txt_records_from_stalwart_dkim_records(self):
        records = build_hosted_dkim_txt_records(
            'example.com',
            [
                {
                    'type': 'TXT',
                    'name': 'tm1._domainkey.example.com.',
                    'content': 'v=DKIM1; k=rsa; p=example',
                },
            ],
        )

        self.assertEqual(
            [{'type': 'TXT', 'name': 'tm1.example.com.dkim.example.net', 'content': 'v=DKIM1; k=rsa; p=example'}],
            records,
        )

    def test_builds_hosted_txt_record_names_for_all_selectors(self):
        records = build_hosted_dkim_txt_record_names('Example.COM.')

        self.assertEqual(
            [
                'tm1.example.com.dkim.example.net',
                'tm2.example.com.dkim.example.net',
                'tm3.example.com.dkim.example.net',
            ],
            records,
        )

    def test_deletes_hosted_txt_records_for_all_selectors(self):
        dns_client = Mock()
        dns_client.delete_txt_records.side_effect = [['record-1'], [], ['record-3']]

        records = delete_hosted_dkim_txt_records('Example.COM.', dns_client=dns_client)

        dns_client.delete_txt_records.assert_has_calls(
            [
                call('tm1.example.com.dkim.example.net'),
                call('tm2.example.com.dkim.example.net'),
                call('tm3.example.com.dkim.example.net'),
            ]
        )
        self.assertEqual(
            [
                {
                    'type': 'TXT',
                    'name': 'tm1.example.com.dkim.example.net',
                    'deleted_record_ids': ['record-1'],
                },
                {
                    'type': 'TXT',
                    'name': 'tm2.example.com.dkim.example.net',
                    'deleted_record_ids': [],
                },
                {
                    'type': 'TXT',
                    'name': 'tm3.example.com.dkim.example.net',
                    'deleted_record_ids': ['record-3'],
                },
            ],
            records,
        )


class DkimSignatureConversionTestCase(SimpleTestCase):
    def test_converts_ed25519_jmap_signature_to_dns_record(self):
        public_pem, expected_public_key = _ed25519_public_key()

        records = dkim_signatures_to_dns_records(
            'example.com',
            [{'id': 'sig-1', 'selector': 'tm2', 'publicKey': public_pem, 'stage': 'active'}],
        )

        self.assertEqual(
            [
                {
                    'type': 'TXT',
                    'name': 'tm2._domainkey.example.com.',
                    'content': f'v=DKIM1; k=ed25519; h=sha256; p={expected_public_key}',
                }
            ],
            records,
        )

    def test_converts_rsa_jmap_signature_to_dns_record(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        expected_public_key = base64.b64encode(
            public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        ).decode()

        records = dkim_signatures_to_dns_records(
            'example.com',
            [{'id': 'sig-1', 'selector': 'tm1', 'publicKey': public_pem, 'stage': 'active'}],
        )

        self.assertEqual(
            [
                {
                    'type': 'TXT',
                    'name': 'tm1._domainkey.example.com.',
                    'content': f'v=DKIM1; k=rsa; h=sha256; p={expected_public_key}',
                }
            ],
            records,
        )

    def test_converts_pending_and_retiring_signatures_to_dns_records(self):
        public_pem, expected_public_key = _ed25519_public_key()

        records = dkim_signatures_to_dns_records(
            'example.com',
            [
                {'id': 'sig-1', 'selector': 'tm1', 'publicKey': public_pem, 'stage': 'pending'},
                {'id': 'sig-2', 'selector': 'tm2', 'publicKey': public_pem, 'stage': 'retiring'},
            ],
        )

        self.assertEqual(
            [
                {
                    'type': 'TXT',
                    'name': 'tm1._domainkey.example.com.',
                    'content': f'v=DKIM1; k=ed25519; h=sha256; p={expected_public_key}',
                },
                {
                    'type': 'TXT',
                    'name': 'tm2._domainkey.example.com.',
                    'content': f'v=DKIM1; k=ed25519; h=sha256; p={expected_public_key}',
                },
            ],
            records,
        )

    def test_skips_retired_signatures(self):
        public_pem, _expected_public_key = _ed25519_public_key()

        records = dkim_signatures_to_dns_records(
            'example.com',
            [{'id': 'sig-1', 'selector': 'tm3', 'publicKey': public_pem, 'stage': 'retired'}],
        )

        self.assertEqual([], records)

    def test_raises_for_missing_signature_stage(self):
        public_pem, _expected_public_key = _ed25519_public_key()

        with self.assertRaisesRegex(RuntimeError, "unexpected stage None"):
            dkim_signatures_to_dns_records(
                'example.com',
                [{'id': 'sig-1', 'selector': 'tm3', 'publicKey': public_pem}],
            )

    def test_raises_for_unknown_signature_stage(self):
        public_pem, _expected_public_key = _ed25519_public_key()

        with self.assertRaisesRegex(RuntimeError, "unexpected stage 'revoked'"):
            dkim_signatures_to_dns_records(
                'example.com',
                [{'id': 'sig-1', 'selector': 'tm3', 'publicKey': public_pem, 'stage': 'revoked'}],
            )


@override_settings(HOSTED_DKIM_CLOUDFLARE_ZONE_ID='zone-id')
class CloudflareDNSClientTestCase(SimpleTestCase):
    def test_creates_txt_record_when_missing(self):
        cloudflare_client = Mock()
        cloudflare_client.dns.records.list.return_value = _cloudflare_page([])
        dns_client = CloudflareDNSClient(api_token='secret', client=cloudflare_client)

        dns_client.upsert_txt_record('tm1.example.com.dkim.example.net', 'v=DKIM1; p=example')

        cloudflare_client.dns.records.create.assert_called_once_with(
            zone_id='zone-id',
            type='TXT',
            name='tm1.example.com.dkim.example.net',
            content='v=DKIM1; p=example',
            ttl=1,
            comment='Managed by Thunderbird Accounts hosted DKIM',
        )

    def test_updates_txt_record_when_content_differs(self):
        cloudflare_client = Mock()
        cloudflare_client.dns.records.list.return_value = _cloudflare_page(
            [{'id': 'record-id', 'name': 'tm1.example.com.dkim.example.net', 'content': 'old'}]
        )
        dns_client = CloudflareDNSClient(api_token='secret', client=cloudflare_client)

        dns_client.upsert_txt_record('tm1.example.com.dkim.example.net', 'new')

        cloudflare_client.dns.records.update.assert_called_once_with(
            'record-id',
            zone_id='zone-id',
            type='TXT',
            name='tm1.example.com.dkim.example.net',
            content='new',
            ttl=1,
            comment='Managed by Thunderbird Accounts hosted DKIM',
        )

    def test_does_not_update_txt_record_when_content_matches(self):
        cloudflare_client = Mock()
        cloudflare_client.dns.records.list.return_value = _cloudflare_page(
            [{'id': 'record-id', 'name': 'tm1.example.com.dkim.example.net', 'content': '"same"'}]
        )
        dns_client = CloudflareDNSClient(api_token='secret', client=cloudflare_client)

        dns_client.upsert_txt_record('tm1.example.com.dkim.example.net', 'same')

        cloudflare_client.dns.records.update.assert_not_called()
        cloudflare_client.dns.records.create.assert_not_called()

    def test_deletes_all_txt_records_for_name(self):
        cloudflare_client = Mock()
        cloudflare_client.dns.records.list.return_value = _cloudflare_page(
            [
                {'id': 'record-1', 'name': 'tm1.example.com.dkim.example.net', 'content': 'one'},
                {'id': 'record-2', 'name': 'tm1.example.com.dkim.example.net', 'content': 'two'},
            ]
        )
        dns_client = CloudflareDNSClient(api_token='secret', client=cloudflare_client)

        deleted_record_ids = dns_client.delete_txt_records('tm1.example.com.dkim.example.net')

        cloudflare_client.dns.records.list.assert_called_once_with(
            zone_id='zone-id',
            type='TXT',
            name={'exact': 'tm1.example.com.dkim.example.net'},
        )
        cloudflare_client.dns.records.delete.assert_has_calls(
            [
                call('record-1', zone_id='zone-id'),
                call('record-2', zone_id='zone-id'),
            ]
        )
        self.assertEqual(['record-1', 'record-2'], deleted_record_ids)

    def test_delete_txt_records_returns_empty_list_when_missing(self):
        cloudflare_client = Mock()
        cloudflare_client.dns.records.list.return_value = _cloudflare_page([])
        dns_client = CloudflareDNSClient(api_token='secret', client=cloudflare_client)

        deleted_record_ids = dns_client.delete_txt_records('tm1.example.com.dkim.example.net')

        cloudflare_client.dns.records.delete.assert_not_called()
        self.assertEqual([], deleted_record_ids)
