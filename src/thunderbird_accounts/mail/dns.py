import logging
import re
from typing import Optional

import dns.rdatatype as dns_rdatatype
import dns.resolver as dns_resolver
from django.conf import settings

from thunderbird_accounts.mail.autodiscover_probe import exchange_autodiscover_endpoint_exists
from thunderbird_accounts.mail.clients import DNSRecordStatus, StaleDNSRecordCode

TXT_TAG_SPEC_RE = re.compile(
    r'[ \t]*(?P<tag>[A-Za-z][A-Za-z0-9_]*)[ \t]*=[ \t]*'
    r'(?P<value>(?:[!-:<-~]+(?:[ \t]+[!-:<-~]+)*)?)[ \t]*'
)
DMARC_VERSION_TAG_RE = re.compile(r'^[ \t]*v[ \t]*=')
VALID_DMARC_POLICIES = {'none', 'quarantine', 'reject'}


def normalize_dns_query_name(name: str, domain_name: str) -> str:
    if name == '@':
        return f'{domain_name.rstrip(".")}.'
    return name if name.endswith('.') else f'{name}.'


def txt_tag_value(content: str, tag: str) -> Optional[str]:
    tags = _parse_txt_tag_value_list(content)
    if tags is None:
        return None
    return dict(tags).get(tag)


def normalize_txt_content(content: str) -> str:
    return ' '.join(content.split())


def check_mx_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    expected_host = record['content'].rstrip('.').lower()
    expected_priority = int(record.get('priority', '10'))

    try:
        answers = dns_resolver.resolve(query_name, 'MX')
    except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
        logging.debug(f'MX lookup failed for {query_name} resulted in NXDOMAIN')
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'MX lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = []
    has_match = False
    same_priority_conflicts = []

    for rdata in answers:
        exchange = rdata.exchange.to_text().rstrip('.')
        preference = rdata.preference
        live_value = f'{preference} {exchange}'
        live_values.append(live_value)
        if exchange.lower() == expected_host and preference == expected_priority:
            has_match = True
        elif preference == expected_priority:
            same_priority_conflicts.append(live_value)

    if has_match:
        if same_priority_conflicts:
            logging.debug(
                f'MX lookup for {query_name} resulted in same-priority conflict with {same_priority_conflicts}'
            )
            return DNSRecordStatus.CONFLICT, same_priority_conflicts
        return DNSRecordStatus.MATCH, []
    if live_values:
        logging.debug(f'MX lookup for {query_name} resulted in conflict with {live_values}')
        return DNSRecordStatus.CONFLICT, live_values
    return DNSRecordStatus.MISSING, []


def check_srv_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    content_parts = record['content'].split()
    expected_weight = int(content_parts[0])
    expected_port = int(content_parts[1])
    expected_target = content_parts[2].rstrip('.').lower()
    expected_priority = int(record.get('priority', '0'))

    try:
        answers = dns_resolver.resolve(query_name, 'SRV')
    except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'SRV lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = []
    has_match = False

    for rdata in answers:
        target = rdata.target.to_text().rstrip('.')
        live_value = f'{rdata.priority} {rdata.weight} {rdata.port} {target}'
        live_values.append(live_value)
        if (
            rdata.priority == expected_priority
            and rdata.weight == expected_weight
            and rdata.port == expected_port
            and target.lower() == expected_target
        ):
            has_match = True

    if has_match:
        return DNSRecordStatus.MATCH, []
    if live_values:
        return DNSRecordStatus.CONFLICT, live_values
    return DNSRecordStatus.MISSING, []


def check_cname_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    expected_target = record['content'].rstrip('.').lower()

    try:
        answers = dns_resolver.resolve(query_name, 'CNAME')
    except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'CNAME lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = [rdata.target.to_text().rstrip('.') for rdata in answers]

    if any(value.lower() == expected_target for value in live_values):
        return DNSRecordStatus.MATCH, []
    if live_values:
        return DNSRecordStatus.CONFLICT, live_values
    return DNSRecordStatus.MISSING, []


def _compare_dkim_txt(expected_content: str, live_values: list[str]) -> tuple[DNSRecordStatus, list[str]]:
    expected_p = txt_tag_value(expected_content, 'p')
    dkim_values = [value for value in live_values if 'v=DKIM1' in value]

    if not dkim_values:
        return DNSRecordStatus.MISSING, []

    if expected_p and any(txt_tag_value(value, 'p') == expected_p for value in dkim_values):
        return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, dkim_values


def _parse_txt_tag_value_list(content: str) -> Optional[list[tuple[str, str]]]:
    parts = content.strip().split(';')
    # Remove empty segments.
    if parts and not parts[-1].strip():
        parts.pop()
    if not parts:
        return None

    tags = []
    seen_tags = set()
    for part in parts:
        match = TXT_TAG_SPEC_RE.fullmatch(part)
        if not match:
            return None

        tag = match.group('tag')
        if tag in seen_tags:
            return None

        seen_tags.add(tag)
        tags.append((tag, match.group('value')))

    return tags


def _is_valid_dmarc_record(tags: list[tuple[str, str]]) -> bool:
    tag_values = dict(tags)
    return tags[0] == ('v', 'DMARC1') and tag_values.get('p') in VALID_DMARC_POLICIES


def _is_dmarc_record_candidate(content: str, tags: Optional[list[tuple[str, str]]]) -> bool:
    if tags is None:
        return bool(DMARC_VERSION_TAG_RE.match(content))
    tag_values = dict(tags)
    return 'v' in tag_values or 'p' in tag_values


def _verify_dmarc(live_values: list[str]) -> tuple[DNSRecordStatus, list[str]]:
    invalid_dmarc_values = []
    for value in live_values:
        tags = _parse_txt_tag_value_list(value)
        if tags and _is_valid_dmarc_record(tags):
            return DNSRecordStatus.MATCH, []
        if _is_dmarc_record_candidate(value, tags):
            invalid_dmarc_values.append(value)

    if invalid_dmarc_values:
        return DNSRecordStatus.CONFLICT, invalid_dmarc_values

    return DNSRecordStatus.MISSING, []


def _compare_spf_txt(expected_content: str, live_values: list[str]) -> tuple[DNSRecordStatus, list[str]]:
    spf_values = [value for value in live_values if value.startswith('v=spf1')]

    if not spf_values:
        return DNSRecordStatus.MISSING, []

    expected_include = next(
        (part.strip() for part in expected_content.split() if part.strip().startswith('include:')),
        None,
    )

    for value in spf_values:
        if expected_include and expected_include in value.split():
            if len(spf_values) == 1:
                return DNSRecordStatus.MATCH, []
            conflicting = [candidate for candidate in spf_values if expected_include not in candidate.split()]
            if conflicting:
                return DNSRecordStatus.CONFLICT, spf_values
            return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, spf_values


def _compare_semantic_txt(
    expected_content: str, live_values: list[str], *, prefix: str
) -> tuple[DNSRecordStatus, list[str]]:
    relevant_values = [value for value in live_values if value.startswith(prefix)]

    if not relevant_values:
        return DNSRecordStatus.MISSING, []

    normalized_expected = normalize_txt_content(expected_content)
    if any(normalize_txt_content(value) == normalized_expected for value in relevant_values):
        return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, relevant_values


def check_txt_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    query_name = normalize_dns_query_name(record['name'], domain_name)
    expected_content = record['content']

    try:
        answers = dns_resolver.resolve(query_name, 'TXT')
    except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        logging.warning(f'TXT lookup failed for {query_name}: {e}')
        return DNSRecordStatus.UNKNOWN, []

    live_values = [b''.join(rdata.strings).decode('utf-8') for rdata in answers]

    if '_domainkey' in query_name:
        return _compare_dkim_txt(expected_content, live_values)
    if expected_content.startswith('v=spf1'):
        return _compare_spf_txt(expected_content, live_values)
    if query_name.startswith('_dmarc.'):
        return _verify_dmarc(live_values)
    if query_name.startswith('_mta-sts.'):
        return _compare_semantic_txt(expected_content, live_values, prefix='v=STSv1')
    if query_name.startswith('_smtp._tls.'):
        return _compare_semantic_txt(expected_content, live_values, prefix='v=TLSRPTv1')

    return DNSRecordStatus.UNKNOWN, []


def check_dns_record_status(domain_name: str, record: dict) -> tuple[DNSRecordStatus, list[str]]:
    """Check customer domain_name against record with expected values"""
    record_type = record.get('type', '').upper()
    if record_type == 'MX':
        return check_mx_record_status(domain_name, record)
    if record_type == 'SRV':
        return check_srv_record_status(domain_name, record)
    if record_type == 'CNAME':
        return check_cname_record_status(domain_name, record)
    if record_type == 'TXT':
        return check_txt_record_status(domain_name, record)
    return DNSRecordStatus.UNKNOWN, []


def enrich_dns_records_with_status(domain_name: str, expected_records: list[dict]) -> list[dict]:
    enriched_records = []
    for record in expected_records:
        status, existing_values = check_dns_record_status(domain_name, record)
        enriched = {**record, 'status': status.value}
        if existing_values:
            enriched['existing_values'] = existing_values
        enriched_records.append(enriched)
    logging.debug('Returning DNS records with status: %s', enriched_records)
    return enriched_records


def _stale_dns_resolve(resolver: dns_resolver.Resolver, name: str, rdtype: str):
    """Thin wrapper so callers don't repeat the exception tuple."""
    return resolver.resolve(name, rdtype)


def _unique_dns_values(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _cname_targets_from_rdata(records) -> list[str]:
    return _unique_dns_values([rdata.target.to_text().rstrip('.') for rdata in records])


def _cname_targets_from_response(answer) -> list[str]:
    targets = []
    for rrset in getattr(getattr(answer, 'response', None), 'answer', []):
        if rrset.rdtype == dns_rdatatype.CNAME:
            targets.extend(rdata.target.to_text().rstrip('.') for rdata in rrset)
    return _unique_dns_values(targets)


def _resolve_autodiscover_cname_targets(resolver: dns_resolver.Resolver, name: str) -> list[str]:
    """Return CNAME targets, including chains visible only through address lookups."""
    targets = []
    try:
        targets.extend(_cname_targets_from_rdata(_stale_dns_resolve(resolver, name, 'CNAME')))
        if targets:
            return _unique_dns_values(targets)
    except (dns_resolver.NoAnswer, dns_resolver.NoNameservers):
        pass
    except dns_resolver.NXDOMAIN:
        return []
    except Exception as e:
        logging.warning(f'CNAME lookup failed for {name}: {e}')

    for rdtype in ('A', 'AAAA'):
        try:
            answer = _stale_dns_resolve(resolver, name, rdtype)
        except (dns_resolver.NoAnswer, dns_resolver.NoNameservers):
            continue
        except dns_resolver.NXDOMAIN:
            return _unique_dns_values(targets)
        except Exception as e:
            logging.warning(f'{rdtype} lookup failed for {name}: {e}')
            continue

        targets.extend(_cname_targets_from_response(answer))

    return _unique_dns_values(targets)


def _resolve_autodiscover_address_records(resolver: dns_resolver.Resolver, name: str) -> dict[str, list[str]]:
    """Return direct A/AAAA records for autodiscover, excluding CNAME target addresses."""
    address_records = {}
    for rdtype in ('A', 'AAAA'):
        try:
            answers = _stale_dns_resolve(resolver, name, rdtype)
        except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
            continue
        except Exception as e:
            logging.warning(f'{rdtype} lookup failed for {name}: {e}')
            continue

        if _cname_targets_from_response(answers):
            continue

        live_values = [rdata.to_text() for rdata in answers]
        if live_values:
            address_records[rdtype] = _unique_dns_values(live_values)

    return address_records


def check_stale_dns_records(cust_domain: str) -> list[dict]:
    """Detect DNS records that exist but should be deleted."""
    stale_records = []

    resolver = dns_resolver.Resolver()
    resolver.lifetime = settings.STALE_DNS_LOOKUP_LIFETIME

    # We currently don't show autodiscover records during custom domain setup, so if they point at
    # a real Exchange Autodiscover endpoint we should mark them stale and ask for removal.
    autodiscover_name = f'autodiscover.{cust_domain}'
    cname_targets = _resolve_autodiscover_cname_targets(resolver, autodiscover_name)
    if cname_targets and exchange_autodiscover_endpoint_exists(autodiscover_name, cust_domain):
        stale_records.append(
            {
                'code': StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value,
                'type': 'CNAME',
                'name': autodiscover_name,
                'existing_values': cname_targets,
            }
        )
    else:
        address_record_sets = _resolve_autodiscover_address_records(resolver, autodiscover_name)
        if address_record_sets and exchange_autodiscover_endpoint_exists(autodiscover_name, cust_domain):
            for record_type, address_records in address_record_sets.items():
                stale_records.append(
                    {
                        'code': StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value,
                        'type': record_type,
                        'name': autodiscover_name,
                        'existing_values': address_records,
                    }
                )

    autodiscover_srv_name = f'_autodiscover._tcp.{cust_domain}'
    try:
        answers = _stale_dns_resolve(resolver, autodiscover_srv_name, 'SRV')
        srv_records = [
            {
                'value': f'{rdata.priority} {rdata.weight} {rdata.port} {rdata.target.to_text().rstrip(".")}',
                'target': rdata.target.to_text().rstrip('.'),
            }
            for rdata in answers
        ]
        if srv_records and any(
            exchange_autodiscover_endpoint_exists(record['target'], cust_domain) for record in srv_records
        ):
            stale_records.append(
                {
                    'code': StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value,
                    'type': 'SRV',
                    'name': autodiscover_srv_name,
                    'existing_values': [record['value'] for record in srv_records],
                }
            )
    except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
        pass
    except Exception as e:
        logging.warning(f'SRV lookup failed for {autodiscover_srv_name}: {e}')

    logging.debug('stale DNS records that should be deleted %s', stale_records)
    return stale_records
