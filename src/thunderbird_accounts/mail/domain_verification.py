import datetime
import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from thunderbird_accounts.mail.clients import DomainVerificationErrors, MailClient, StaleDNSRecordCode
from thunderbird_accounts.mail.dns import check_stale_dns_records
from thunderbird_accounts.mail.exceptions import DomainNotFoundError
from thunderbird_accounts.mail.models import Domain
from thunderbird_accounts.mail.types import stalwart


@dataclass
class DomainVerificationResult:
    is_verified: bool
    response_data: dict


def _verification_lock_key(domain_uuid) -> str:
    return f'custom-domain-verification-lock:{domain_uuid}'


def acquire_verification_lock(domain_uuid) -> bool:
    """Returns False if a verification for this domain is already queued or running."""
    return cache.add(_verification_lock_key(domain_uuid), 1, timeout=settings.CUSTOM_DOMAIN_VERIFICATION_LOCK_SECONDS)


def extend_verification_lock(domain_uuid, seconds: int):
    cache.set(_verification_lock_key(domain_uuid), 1, timeout=seconds)


def release_verification_lock(domain_uuid):
    cache.delete(_verification_lock_key(domain_uuid))


def critical_errors_from_stale_dns_records(stale_dns_records: list[dict]) -> list[DomainVerificationErrors]:
    stale_record_codes = {record.get('code') for record in stale_dns_records}
    critical_errors = []

    if StaleDNSRecordCode.AUTODISCOVER_CNAME_UNEXPECTED.value in stale_record_codes:
        critical_errors.append(DomainVerificationErrors.AUTODISCOVER_RECORD_FOUND)
    if StaleDNSRecordCode.AUTODISCOVER_SRV_UNEXPECTED.value in stale_record_codes:
        critical_errors.append(DomainVerificationErrors.AUTODISCOVER_SRV_RECORD_FOUND)

    return critical_errors


def verify_domain(domain: Domain) -> DomainVerificationResult:
    """Checks the domain's DNS, then saves its VERIFIED/FAILED status and provisions it on Stalwart when verified.

    Mail backend and request errors propagate to the caller, which decides how to surface them."""
    now = datetime.datetime.now(datetime.UTC)
    stalwart_client = MailClient()

    dns_check = stalwart_client.check_domain_dns(domain.name)
    if settings.CUSTOM_DOMAINS_DO_VERIFY:
        is_verified = dns_check['is_verified']
        critical_errors = dns_check['critical_errors']
        warnings = dns_check['warnings']
    else:
        is_verified = True
        critical_errors = []
        warnings = [_('Custom domain DNS verification disabled. Automatically verified domain.')]

    domain.last_verification_attempt = now

    dns_records = dns_check['dns_records']
    stale_dns_records = check_stale_dns_records(domain.name)
    stale_dns_critical_errors = critical_errors_from_stale_dns_records(stale_dns_records)
    for critical_error in stale_dns_critical_errors:
        if critical_error not in critical_errors:
            critical_errors.append(critical_error)

    if stale_dns_critical_errors:
        is_verified = False

    response_data = {
        'critical_errors': critical_errors,
        'warnings': warnings,
        'dns_records': dns_records,
        'stale_dns_records': stale_dns_records,
    }

    if not is_verified:
        domain.status = Domain.DomainStatus.FAILED
        domain.save()
        return DomainVerificationResult(is_verified=False, response_data=response_data)

    try:
        stalwart_resp = stalwart_client.get_domain(domain.name)
    except DomainNotFoundError:
        stalwart_resp = None

    # Only roll through these steps if we're not already verified OR stalwart doesn't have our domain
    if domain.status != Domain.DomainStatus.VERIFIED or not stalwart_resp:
        # Deferred: mail.tasks imports this module
        from thunderbird_accounts.mail import tasks as mail_tasks

        domain.status = Domain.DomainStatus.VERIFIED
        domain.verified_at = now

        # Fetch or create a domain on Stalwart's end, and retrieve the domain_id
        if stalwart_resp:
            domain_id = stalwart_resp.get('id')
            # Now we need to enable the domain if it's not already enabled.
            if domain.user.is_migrated and not stalwart_resp.is_enabled:
                stalwart_client.update_domain(domain.name, stalwart.DomainUpdate(is_enabled=True))
        else:
            domain_id = stalwart_client.create_domain(domain.name)

        # Ensure missing DKIM selectors without replacing keys created at domain-add time.
        stalwart_client.ensure_dkim(domain.name)

        mail_tasks.publish_hosted_dkim_dns_records.delay(domain.name)
        if settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
            stalwart_client.activate_pending_dkim_signatures(domain.name)

        if domain_id:
            domain.stalwart_id = domain_id
        else:
            logging.error(f'There was a problem saving the domain id for {domain.name} / {domain.uuid}')

        domain.stalwart_created_at = datetime.datetime.now(datetime.UTC)
        domain.save()

    return DomainVerificationResult(is_verified=True, response_data=response_data)
