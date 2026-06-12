import sentry_sdk
from cryptography.exceptions import UnsupportedAlgorithm
from functools import cache
import base64
import time
from typing import Any

from cloudflare import Cloudflare
from cloudflare.types.dns.record_response import RecordResponse as CloudflareRecordResponse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


HOSTED_DKIM_RECORD_COMMENT = 'Managed by Thunderbird Accounts hosted DKIM'

# Stalwart states used to track key rotations
DKIM_SIGNATURE_STAGES = {'pending', 'active', 'retiring', 'retired'}
# The stages that need to be sync'ed to DNS.
DKIM_SIGNATURE_DNS_STAGES = {'pending', 'active', 'retiring'}


class CloudflareDNSClient:
    """Cloudflare DNS Client
    Handles basic DNS operations against Cloudflare's API.

    Note: If you do not have the settings: HOSTED_DKIM_CLOUDFLARE_ZONE_ID or HOSTED_DKIM_CLOUDFLARE_API_TOKEN set
    then you must past zone_id and/or api_token respectively."""

    def __init__(self, api_token: str | None = None, zone_id: str | None = None, ttl: int | None = None, client=None):
        self.zone_id = zone_id or settings.HOSTED_DKIM_CLOUDFLARE_ZONE_ID
        if not self.zone_id:
            raise ImproperlyConfigured('HOSTED_DKIM_CLOUDFLARE_ZONE_ID must be configured')

        api_token = api_token or settings.HOSTED_DKIM_CLOUDFLARE_API_TOKEN
        if client is None and not api_token:
            raise ImproperlyConfigured('HOSTED_DKIM_CLOUDFLARE_API_TOKEN must be configured')

        self.ttl = settings.HOSTED_DKIM_CLOUDFLARE_TTL if ttl is None else ttl
        self.client = client or Cloudflare(api_token=api_token)

    def _list_txt_records(self, name: str) -> list[CloudflareRecordResponse]:
        return self.client.dns.records.list(
            zone_id=self.zone_id,
            type='TXT',
            name={'exact': name},
        ).result

    def upsert_txt_record(self, name: str, content: str) -> CloudflareRecordResponse | None:
        records = self._list_txt_records(name)
        if records:
            record = records[0]
            if _normalize_txt_content(_record_value(record, 'content')) == _normalize_txt_content(content):
                return record

            return self.client.dns.records.update(
                _record_value(record, 'id'),
                zone_id=self.zone_id,
                type='TXT',
                name=name,
                content=content,
                ttl=self.ttl,
                comment=HOSTED_DKIM_RECORD_COMMENT,
            )

        return self.client.dns.records.create(
            zone_id=self.zone_id,
            type='TXT',
            name=name,
            content=content,
            ttl=self.ttl,
            comment=HOSTED_DKIM_RECORD_COMMENT,
        )

    def delete_txt_records(self, name: str) -> list[str]:
        records = self._list_txt_records(name)
        deleted_record_ids = []

        for record in records:
            record_id = _record_value(record, 'id')
            if not record_id:
                continue

            self.client.dns.records.delete(record_id, zone_id=self.zone_id)
            deleted_record_ids.append(record_id)

        return deleted_record_ids


@cache
def _normalize_domain(domain_name: str) -> str:
    """Normalizes domain names by lowercasing them, stripping out trailing spaces,
    and removing any ending periods (like those at the end of dns records.)"""
    return domain_name.strip().rstrip('.').lower()


@cache
def _normalize_txt_content(content: str | None) -> str:
    """Normalizes txt content by removing any leading and trailing whitespace and quotes"""
    if content is None:
        return ''

    return content.strip('" ')


def _record_value(record: dict | CloudflareRecordResponse, field: str) -> Any:
    """Helper function to retrieve a field from either a dict or a Cloudflare record object"""
    if isinstance(record, dict):
        return record.get(field)
    return getattr(record, field, None)


@cache
def _selector_from_dkim_name(record_name: str, domain_name: str) -> str | None:
    """Retrieves the selector from a dkim dns entry."""
    record_name = _normalize_domain(record_name)
    domain_name = _normalize_domain(domain_name)
    suffix = f'._domainkey.{domain_name}'
    if not record_name.endswith(suffix):
        return None
    selector = record_name[: -len(suffix)]
    return selector or None


def _dkim_key_type_and_public_key_value(signature: dict) -> tuple[str, str]:
    """Retrieves and base64 encodes the publicKey from a signature

    :raises RuntimeError: On an unsupported or invalid DKIM public key"""
    public_key = signature.get('publicKey')
    if not public_key:
        raise RuntimeError(f'DKIM signature {signature.get("id")} did not include a public key')

    try:
        public_key_obj = serialization.load_pem_public_key(public_key.encode())
    except (ValueError, UnsupportedAlgorithm) as ex:
        sentry_sdk.capture_exception(ex)
        public_key_obj = None

    if isinstance(public_key_obj, ed25519.Ed25519PublicKey):
        key_type = 'ed25519'
        key_bytes = public_key_obj.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    elif isinstance(public_key_obj, rsa.RSAPublicKey):
        key_type = 'rsa'
        key_bytes = public_key_obj.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    else:
        raise RuntimeError(f'Unsupported DKIM public key type for signature {signature.get("id")}')

    return key_type, base64.b64encode(key_bytes).decode()


def hosted_dkim_record_name(selector: str, domain_name: str, hosted_domain: str | None = None) -> str:
    """Returns a normalized dkim record name.
    If hosted domain is not specified it falls back on ``settings.HOSTED_DKIM_DOMAIN``"""
    hosted_domain = hosted_domain or settings.HOSTED_DKIM_DOMAIN
    if not hosted_domain:
        raise ImproperlyConfigured(
            'hosted_domain not provided and HOSTED_DKIM_DOMAIN is empty.'
            ' One must be configured to build hosted DKIM records'
        )
    return f'{selector}.{_normalize_domain(domain_name)}.{_normalize_domain(hosted_domain)}'


def build_customer_dkim_cname_records(domain_name: str, hosted_domain: str | None = None) -> list[dict[str, str]]:
    """Builds dkim CNAME dns records for a given domain name.
    If hosted domain is not specified it falls back on ``settings.HOSTED_DKIM_DOMAIN``"""
    hosted_domain = hosted_domain or settings.HOSTED_DKIM_DOMAIN
    if not hosted_domain:
        return []

    domain_name = _normalize_domain(domain_name)
    return [
        {
            'type': 'CNAME',
            'name': f'{selector}._domainkey.{domain_name}.',
            'content': f'{hosted_dkim_record_name(selector, domain_name, hosted_domain)}.',
            'priority': '-',
        }
        for selector in settings.HOSTED_DKIM_SELECTORS
    ]


def build_hosted_dkim_txt_record_names(domain_name: str, hosted_domain: str | None = None) -> list[str]:
    """Builds hosted DKIM TXT record names for a given domain name.
    If hosted domain is not specified it falls back on ``settings.HOSTED_DKIM_DOMAIN``"""
    hosted_domain = hosted_domain or settings.HOSTED_DKIM_DOMAIN
    if not hosted_domain:
        return []

    domain_name = _normalize_domain(domain_name)
    return [
        hosted_dkim_record_name(selector, domain_name, hosted_domain) for selector in settings.HOSTED_DKIM_SELECTORS
    ]


def build_hosted_dkim_txt_records(domain_name: str, dkim_dns_records: list[dict]) -> list[dict[str, str]]:
    """Builds dkim TXT dns records for a given domain name.
    If hosted domain is not specified it falls back on ``settings.HOSTED_DKIM_DOMAIN``"""
    records = []
    managed_selectors = set(settings.HOSTED_DKIM_SELECTORS)
    for record in dkim_dns_records:
        selector = _selector_from_dkim_name(record.get('name', ''), domain_name)
        content = record.get('content')
        if not selector or selector not in managed_selectors or not content:
            continue

        records.append(
            {
                'type': 'TXT',
                'name': hosted_dkim_record_name(selector, domain_name),
                'content': content,
            }
        )
    return records


def dkim_signatures_to_dns_records(domain_name: str, signatures: list[dict]) -> list[dict[str, str]]:
    """Builds a dkim TXT dns record with the given dkim signatures.

    :raises RuntimeError: On an invalid public key or dkim signature"""
    domain_name = _normalize_domain(domain_name)
    records = []

    for signature in signatures:
        selector = signature.get('selector')
        if not selector:
            continue

        stage = signature.get('stage')
        if stage not in DKIM_SIGNATURE_STAGES:
            raise RuntimeError(f'DKIM signature {signature.get("id")} had unexpected stage {stage!r}')

        if stage not in DKIM_SIGNATURE_DNS_STAGES:
            continue

        key_type, public_key_value = _dkim_key_type_and_public_key_value(signature)

        records.append(
            {
                'type': 'TXT',
                'name': f'{selector}._domainkey.{domain_name}.',
                'content': f'v=DKIM1; k={key_type}; h=sha256; p={public_key_value}',
            }
        )

    return records


def publish_hosted_dkim_txt_records(
    hosted_records: list[dict[str, str]],
    dns_client=None,
    throttle_seconds: float = 0.0,
) -> list[dict[str, str]]:
    """Publishes hosted DKIM TXT records.
    If dns_client is not specified it falls back on ``CloudflareDNSClient``"""
    dns_client = dns_client or CloudflareDNSClient()

    for record in hosted_records:
        dns_client.upsert_txt_record(record['name'], record['content'])
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

    return hosted_records


def delete_hosted_dkim_txt_records(domain_name: str, dns_client=None) -> list[dict[str, str | list[str]]]:
    """Deletes hosted DKIM TXT records for a given domain name.
    If dns_client is not specified it falls back on ``CloudflareDNSClient``"""
    dns_client = dns_client or CloudflareDNSClient()

    deleted_records = []
    for name in build_hosted_dkim_txt_record_names(domain_name):
        deleted_records.append(
            {
                'type': 'TXT',
                'name': name,
                'deleted_record_ids': dns_client.delete_txt_records(name),
            }
        )

    return deleted_records
