import base64
from typing import Any

from cloudflare import Cloudflare
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


HOSTED_DKIM_RECORD_COMMENT = 'Managed by Thunderbird Accounts hosted DKIM'


def _normalize_domain(domain_name: str) -> str:
    return domain_name.strip().rstrip('.').lower()


def _normalize_txt_content(content: str | None) -> str:
    if content is None:
        return ''
    content = content.strip()
    if len(content) >= 2 and content[0] == '"' and content[-1] == '"':
        return content[1:-1]
    return content


def _record_value(record: Any, field: str) -> Any:
    if isinstance(record, dict):
        return record.get(field)
    return getattr(record, field, None)


def _selector_from_dkim_name(record_name: str, domain_name: str) -> str | None:
    record_name = _normalize_domain(record_name)
    domain_name = _normalize_domain(domain_name)
    suffix = f'._domainkey.{domain_name}'
    if not record_name.endswith(suffix):
        return None
    selector = record_name[: -len(suffix)]
    return selector or None


def hosted_dkim_record_name(selector: str, domain_name: str, hosted_domain: str | None = None) -> str:
    hosted_domain = hosted_domain or settings.HOSTED_DKIM_DOMAIN
    if not hosted_domain:
        raise ImproperlyConfigured('HOSTED_DKIM_DOMAIN must be configured to build hosted DKIM records')
    return f'{selector}.{_normalize_domain(domain_name)}.{_normalize_domain(hosted_domain)}'


def build_customer_dkim_cname_records(domain_name: str, hosted_domain: str | None = None) -> list[dict[str, str]]:
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


def build_hosted_dkim_txt_records(domain_name: str, dkim_dns_records: list[dict]) -> list[dict[str, str]]:
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


def _dkim_key_type_and_public_key_value(signature: dict) -> tuple[str, str]:
    public_key = signature.get('publicKey')
    if not public_key:
        raise RuntimeError(f'DKIM signature {signature.get("id")} did not include a public key')

    public_key_obj = serialization.load_pem_public_key(public_key.encode())
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


def dkim_signatures_to_dns_records(domain_name: str, signatures: list[dict]) -> list[dict[str, str]]:
    domain_name = _normalize_domain(domain_name)
    records = []

    for signature in signatures:
        selector = signature.get('selector')
        if not selector:
            continue

        if signature.get('stage', 'active') != 'active':
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


class CloudflareDNSClient:
    def __init__(self, api_token: str | None = None, zone_id: str | None = None, ttl: int | None = None, client=None):
        self.zone_id = zone_id or settings.HOSTED_DKIM_CLOUDFLARE_ZONE_ID
        if not self.zone_id:
            raise ImproperlyConfigured('HOSTED_DKIM_CLOUDFLARE_ZONE_ID must be configured')

        api_token = api_token or settings.HOSTED_DKIM_CLOUDFLARE_API_TOKEN
        if client is None and not api_token:
            raise ImproperlyConfigured('HOSTED_DKIM_CLOUDFLARE_API_TOKEN must be configured')

        self.ttl = settings.HOSTED_DKIM_CLOUDFLARE_TTL if ttl is None else ttl
        self.client = client or Cloudflare(api_token=api_token)

    def _list_txt_records(self, name: str):
        return self.client.dns.records.list(
            zone_id=self.zone_id,
            type='TXT',
            name={'exact': name},
        ).result

    def upsert_txt_record(self, name: str, content: str):
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


def publish_hosted_dkim_txt_records(
    domain_name: str, dkim_dns_records: list[dict], dns_client=None
) -> list[dict[str, str]]:
    dns_client = dns_client or CloudflareDNSClient()
    hosted_records = build_hosted_dkim_txt_records(domain_name, dkim_dns_records)

    for record in hosted_records:
        dns_client.upsert_txt_record(record['name'], record['content'])

    return hosted_records
