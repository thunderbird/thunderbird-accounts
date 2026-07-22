# =====================================================================================
# Mail client interface + shared enums
# -------------------------------------------------------------------------------------
# The abstract surface every mail client implementation (JMAP for Stalwart v0.16,
# legacy REST for v0.15) must satisfy. Callers import `MailClient` (bound to the JMAP
# implementation in this package's __init__) plus these enums; keep this the single home
# for the shared enums so re-exports stay stable.
# =====================================================================================

from __future__ import annotations

from enum import StrEnum
from typing import Optional


class StalwartErrors(StrEnum):
    """Errors defined in Stalwart's (legacy v0.15) management api.

    Retained for backwards compatibility; v0.16 surfaces failures as JMAP SetError
    maps (notCreated/notUpdated/notDestroyed) and method-level ["error", {...}] tuples.
    """

    FIELD_ALREADY_EXISTS = 'fieldAlreadyExists'
    FIELD_MISSING = 'fieldMissing'
    NOT_FOUND = 'notFound'
    UNSUPPORTED = 'unsupported'
    ASSERT_FAILED = 'assertFailed'
    OTHER = 'other'


class DomainVerificationErrors(StrEnum):
    """Domain verification error codes returned by check_domain_dns()."""

    # Critical errors (fail verification)
    MX_LOOKUP_ERROR = 'mxLookupError'
    DKIM_RECORD_NOT_FOUND = 'dkimRecordNotFound'
    AUTODISCOVER_RECORD_FOUND = 'autodiscoverRecordFound'
    AUTODISCOVER_SRV_RECORD_FOUND = 'autodiscoverSrvRecordFound'

    # Warnings (do not fail verification)
    SPF_RECORD_NOT_FOUND = 'spfRecordNotFound'


class DkimSignatureStage(StrEnum):
    """Stalwart DKIM signature rotation stages."""

    PENDING = 'pending'
    ACTIVE = 'active'
    RETIRING = 'retiring'
    RETIRED = 'retired'


class DNSRecordStatus(StrEnum):
    MATCH = 'match'
    CONFLICT = 'conflict'
    MISSING = 'missing'
    UNKNOWN = 'unknown'


class StaleDNSRecordCode(StrEnum):
    """Stale DNS records that should be removed to prevent issues with the Thundermail setup."""

    AUTODISCOVER_CNAME_UNEXPECTED = 'autodiscoverCnameUnexpected'
    AUTODISCOVER_SRV_UNEXPECTED = 'autodiscoverSrvUnexpected'


class MailClientInterface:
    """Abstract mail client surface.

    Every public method a caller may rely on is declared here and raises
    NotImplementedError by default. Concrete implementations (``MailClientJMAP``,
    ``MailClientLegacy``) override the ones they support. Kept as a plain base (rather
    than an ``abc.ABC`` with ``@abstractmethod``) so a partial implementation — e.g. the
    legacy reference stub — stays instantiable.

    Return-type contract: ``get_account`` returns the v0.15-compatible dict
    (``id, type, description, emails, secrets, quota, usedQuota`` + raw fields), NOT a
    raw pydantic model, so existing callers keep working.
    """

    # ------------------------------------------------------------------ #
    # Health check
    # ------------------------------------------------------------------ #

    def get_telemetry(self):
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # Accounts
    # ------------------------------------------------------------------ #

    def get_account(self, principal_id: str) -> dict:
        raise NotImplementedError()

    def create_account(
        self,
        emails: list[str],
        principal_id: str,
        full_name: Optional[str] = None,
        app_password: Optional[str] = None,
        quota: Optional[int] = None,
    ):
        raise NotImplementedError()

    def delete_account(self, principal_id: str):
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # App passwords
    # ------------------------------------------------------------------ #

    def save_app_password(self, principal_id: str, secret: str):
        raise NotImplementedError()

    def delete_app_password(self, principal_id: str, secret: str):
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # Email addresses / aliases
    # ------------------------------------------------------------------ #

    def save_email_addresses(self, principal_id: str, emails: str | list[str]):
        raise NotImplementedError()

    def replace_email_addresses(self, principal_id: str, emails: list[tuple[str, str]]):
        raise NotImplementedError()

    def delete_email_addresses(self, principal_id: str, emails: str | list[str]):
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # Account field updates
    # ------------------------------------------------------------------ #

    def update_individual(
        self,
        principal_id: str,
        primary_email_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ):
        raise NotImplementedError()

    def update_quota(self, principal_id: str, quota: int):
        raise NotImplementedError()

    def make_api_key(self, principal_id, password):
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # Domains
    # ------------------------------------------------------------------ #

    def get_domain(self, domain):
        raise NotImplementedError()

    def create_domain(self, domain, description=''):
        raise NotImplementedError()

    def delete_domain(self, domain_name: str):
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # DKIM
    # ------------------------------------------------------------------ #

    def create_dkim(self, domain, stage: DkimSignatureStage = DkimSignatureStage.PENDING, algorithms=None):
        raise NotImplementedError()

    def delete_dkim(self, domain) -> Optional[list]:
        raise NotImplementedError()

    def get_dkim_signatures(self, domain_name: str) -> list[dict]:
        raise NotImplementedError()

    def get_dkim_selectors(self, domain_name: str) -> set[str]:
        raise NotImplementedError()

    def ensure_dkim(self, domain_name: str, stage: DkimSignatureStage = DkimSignatureStage.PENDING) -> list[dict]:
        raise NotImplementedError()

    def activate_pending_dkim_signatures(self, domain_name: str) -> list[str]:
        raise NotImplementedError()

    def get_dkim_dns_records(self, domain_name: str) -> list[dict]:
        raise NotImplementedError()

    # ------------------------------------------------------------------ #
    # DNS records + local verification
    # ------------------------------------------------------------------ #

    def get_dns_records(self, domain_name: str) -> list[dict]:
        raise NotImplementedError()

    def build_expected_dns_records(self, cust_domain: str) -> list[dict]:
        raise NotImplementedError()

    def check_domain_dns(self, domain_name: str) -> dict:
        raise NotImplementedError()
