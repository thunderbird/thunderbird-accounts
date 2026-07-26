import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import dns.resolver as dns_resolver
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpRequest, StreamingHttpResponse
from django.views.decorators.cache import never_cache

from thunderbird_accounts.mail.clients import DNSRecordStatus, MailClient
from thunderbird_accounts.mail.dkim import CloudflareDNSClient
from thunderbird_accounts.mail.models import Domain


TXT_TAG_SPEC_RE = re.compile(
    r'[ \t]*(?P<tag>[A-Za-z][A-Za-z0-9_]*)[ \t]*=[ \t]*'
    r'(?P<value>(?:[!-:<-~]+(?:[ \t]+[!-:<-~]+)*)?)[ \t]*'
)


@dataclass
class BackfillCounters:
    domains_scanned: int = 0
    domains_with_stalwart_dkim: int = 0
    domains_without_stalwart_dkim: int = 0
    records_checked: int = 0
    match: int = 0
    missing: int = 0
    conflict: int = 0
    unknown: int = 0
    applied: int = 0
    failures: int = 0


@never_cache
@staff_member_required
def admin_hosted_dkim_backfill(request: HttpRequest):
    if not request.user or not request.user.is_authenticated or not request.user.is_superuser:
        raise Http404()

    response = StreamingHttpResponse(
        _stream_backfill_response(request),
        content_type='text/plain; charset=utf-8',
    )
    response['X-Accel-Buffering'] = 'no'
    return response


def _stream_backfill_response(request: HttpRequest):
    live = _query_bool(request, 'live')
    domain_name = request.GET.get('domain')

    try:
        limit = _query_positive_int(request, 'limit')
        sleep_seconds = _query_nonnegative_float(request, 'sleep_seconds', default=1.0)
    except ValueError as ex:
        yield _line(f'ERROR: {ex}')
        return

    yield from _supported_query_strings(request)

    try:
        _validate_configuration(live=live)
    except ImproperlyConfigured as ex:
        yield _line(f'ERROR: {ex}')
        return

    mode = 'LIVE' if live else 'DRY-RUN'
    yield _line(f'{mode}: hosted DKIM backfill for selectors {", ".join(settings.HOSTED_DKIM_SELECTORS)}')
    if live:
        yield _line(f'Cloudflare write throttle: {sleep_seconds} seconds after each write.')
    else:
        yield _line('No Cloudflare writes will be made.')
    yield _line('')

    counters = BackfillCounters()
    try:
        yield from _run_backfill(
            counters,
            live=live,
            domain_name=domain_name,
            limit=limit,
            sleep_seconds=sleep_seconds,
        )
    except Exception as ex:
        counters.failures += 1
        yield _line(f'ERROR: {ex}')

    yield from _summary_lines(counters, live=live)


def _run_backfill(
    counters: BackfillCounters,
    *,
    live: bool,
    domain_name: str | None,
    limit: int | None,
    sleep_seconds: float,
):
    stalwart = MailClient()
    dns_client = CloudflareDNSClient() if live else None
    domains = Domain.objects.order_by('name')
    if domain_name:
        domains = domains.filter(name=_normalize_domain(domain_name))
        if not domains.exists():
            yield _line(f'ERROR: Domain {domain_name} was not found in local custom domains.')
            return

    actionable_records = 0
    stopped_at_limit = False
    for domain in domains.iterator():
        counters.domains_scanned += 1
        try:
            hosted_records = _build_hosted_dkim_txt_records(
                domain.name,
                stalwart.get_dkim_dns_records(domain.name),
            )
        except Exception as ex:
            counters.failures += 1
            yield _line(f'ERROR {domain.name}: failed to fetch Stalwart DKIM records: {ex}')
            continue

        if not hosted_records:
            counters.domains_without_stalwart_dkim += 1
            continue

        counters.domains_with_stalwart_dkim += 1
        for record in hosted_records:
            status, existing_values = _check_hosted_dkim_txt_record(record)
            _increment_status(counters, status)
            counters.records_checked += 1

            if status not in {DNSRecordStatus.MISSING, DNSRecordStatus.CONFLICT}:
                if status == DNSRecordStatus.UNKNOWN:
                    yield _line(f'UNKNOWN {domain.name} {record["name"]}')
                    if existing_values:
                        yield _line(f'  lookup error: {existing_values[0]}')
                continue

            actionable_records += 1
            action = 'would upsert' if not live else 'upserting'
            yield _line(f'{status.value.upper()} {domain.name} {record["name"]}: {action}')

            if live:
                try:
                    dns_client.upsert_txt_record(record['name'], record['content'])
                except Exception as ex:
                    counters.failures += 1
                    yield _line(f'ERROR {record["name"]}: Cloudflare upsert failed: {ex}')
                    continue

                counters.applied += 1
                logging.info(f'Backfilled hosted DKIM TXT record {record["name"]} for {domain.name}')
                yield _line(f'UPDATED {domain.name} {record["name"]}')
                if sleep_seconds:
                    time.sleep(sleep_seconds)

            if limit is not None and actionable_records >= limit:
                stopped_at_limit = True
                break

        if stopped_at_limit:
            yield _line(f'Stopped after reaching limit={limit}.')
            break


def _supported_query_strings(request: HttpRequest):
    path = request.path
    yield _line('Supported query strings:')
    yield _line(f'  {path}')
    yield _line(f'  {path}?domain=example.com')
    yield _line(f'  {path}?limit=25')
    yield _line(f'  {path}?live=1&limit=25&sleep_seconds=1')
    yield _line('')


def _summary_lines(counters: BackfillCounters, *, live: bool):
    yield _line('')
    yield _line('Summary')
    yield _line(f'  domains scanned: {counters.domains_scanned}')
    yield _line(f'  domains with Stalwart DKIM records: {counters.domains_with_stalwart_dkim}')
    yield _line(f'  domains without selected Stalwart DKIM records: {counters.domains_without_stalwart_dkim}')
    yield _line(f'  hosted records checked: {counters.records_checked}')
    yield _line(f'  matching records: {counters.match}')
    yield _line(f'  missing records: {counters.missing}')
    yield _line(f'  conflicting records: {counters.conflict}')
    yield _line(f'  unknown records: {counters.unknown}')
    if live:
        yield _line(f'  Cloudflare records upserted: {counters.applied}')
    else:
        yield _line(f'  Cloudflare records that would be upserted: {counters.missing + counters.conflict}')
    yield _line(f'  failures: {counters.failures}')


def _validate_configuration(*, live: bool):
    if not settings.HOSTED_DKIM_DOMAIN:
        raise ImproperlyConfigured('HOSTED_DKIM_DOMAIN must be configured.')
    if not settings.HOSTED_DKIM_SELECTORS:
        raise ImproperlyConfigured('HOSTED_DKIM_SELECTORS must include at least one selector.')
    if live and not settings.HOSTED_DKIM_CLOUDFLARE_ENABLED:
        raise ImproperlyConfigured('HOSTED_DKIM_CLOUDFLARE_ENABLED must be true for live mode.')


def _query_bool(request: HttpRequest, name: str) -> bool:
    value = request.GET.get(name)
    if value is None:
        return False
    return value.lower() in {'1', 'true', 'yes', 'on'}


def _query_positive_int(request: HttpRequest, name: str) -> int | None:
    value = request.GET.get(name)
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as ex:
        raise ValueError(f'{name} must be an integer.') from ex
    if parsed < 1:
        raise ValueError(f'{name} must be greater than 0.')
    return parsed


def _query_nonnegative_float(request: HttpRequest, name: str, *, default: float) -> float:
    value = request.GET.get(name)
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError as ex:
        raise ValueError(f'{name} must be a number.') from ex
    if parsed < 0:
        raise ValueError(f'{name} must be 0 or greater.')
    return parsed


def _normalize_domain(domain_name: str) -> str:
    return domain_name.strip().rstrip('.').lower()


def _hosted_dkim_record_name(selector: str, domain_name: str) -> str:
    return f'{selector}.{_normalize_domain(domain_name)}.{_normalize_domain(settings.HOSTED_DKIM_DOMAIN)}'


def _selector_from_dkim_name(record_name: str, domain_name: str) -> str | None:
    record_name = _normalize_domain(record_name)
    domain_name = _normalize_domain(domain_name)
    suffix = f'._domainkey.{domain_name}'
    if not record_name.endswith(suffix):
        return None
    selector = record_name[: -len(suffix)]
    return selector or None


def _build_hosted_dkim_txt_records(domain_name: str, dkim_dns_records: list[dict]) -> list[dict[str, str]]:
    records = []
    managed_selectors = {_normalize_domain(selector) for selector in settings.HOSTED_DKIM_SELECTORS}
    for record in dkim_dns_records:
        selector = _selector_from_dkim_name(record.get('name', ''), domain_name)
        content = record.get('content')
        if not selector or selector not in managed_selectors or not content:
            continue

        records.append(
            {
                'type': 'TXT',
                'name': _hosted_dkim_record_name(selector, domain_name),
                'content': content,
            }
        )
    return records


def _check_hosted_dkim_txt_record(record: dict[str, str]) -> tuple[DNSRecordStatus, list[str]]:
    query_name = record['name'] if record['name'].endswith('.') else f'{record["name"]}.'
    try:
        answers = dns_resolver.resolve(query_name, 'TXT')
    except (dns_resolver.NoAnswer, dns_resolver.NXDOMAIN, dns_resolver.NoNameservers):
        return DNSRecordStatus.MISSING, []
    except Exception as e:
        return DNSRecordStatus.UNKNOWN, [str(e)]

    live_values = [b''.join(rdata.strings).decode('utf-8') for rdata in answers]
    return _compare_dkim_txt(record['content'], live_values)


def _compare_dkim_txt(expected_content: str, live_values: list[str]) -> tuple[DNSRecordStatus, list[str]]:
    expected_p = _txt_tag_value(expected_content, 'p')
    dkim_values = [value for value in live_values if 'v=DKIM1' in value]

    if not dkim_values:
        return DNSRecordStatus.MISSING, []

    if expected_p and any(_txt_tag_value(value, 'p') == expected_p for value in dkim_values):
        return DNSRecordStatus.MATCH, []

    return DNSRecordStatus.CONFLICT, dkim_values


def _txt_tag_value(content: str, tag: str) -> Optional[str]:
    tags = _parse_txt_tag_value_list(content)
    if tags is None:
        return None
    return dict(tags).get(tag)


def _parse_txt_tag_value_list(content: str) -> Optional[list[tuple[str, str]]]:
    parts = content.strip().split(';')
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


def _increment_status(counters: BackfillCounters, status: DNSRecordStatus):
    if status == DNSRecordStatus.MATCH:
        counters.match += 1
    elif status == DNSRecordStatus.MISSING:
        counters.missing += 1
    elif status == DNSRecordStatus.CONFLICT:
        counters.conflict += 1
    elif status == DNSRecordStatus.UNKNOWN:
        counters.unknown += 1


def _line(value: str) -> str:
    return f'{value}\n'
