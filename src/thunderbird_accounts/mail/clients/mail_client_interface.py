from enum import StrEnum
from typing import Optional

import requests


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


class MailClientInterface:
    def get_telemetry(self):
        raise NotImplementedError()

    def get_domain(self, domain):
        raise NotImplementedError()

    def create_dkim(self, domain, stage: DkimSignatureStage = DkimSignatureStage.PENDING, algorithms=None):
        raise NotImplementedError()

    def get_dkim_selectors(self, domain_name: str) -> set[str]:
        raise NotImplementedError()

    def ensure_dkim(self, domain_name: str, stage: DkimSignatureStage = DkimSignatureStage.PENDING) -> list[dict]:
        raise NotImplementedError()

    def activate_pending_dkim_signatures(self, domain_name: str) -> list[str]:
        raise NotImplementedError()

    def delete_dkim(self, domain) -> Optional[requests.Response]:
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

    def get_account(self, principal_id: str):# -> dict:
        raise NotImplementedError()

    def delete_account(self, principal_id: str):
        raise NotImplementedError()

    def delete_app_password(self, principal_id: str, secret: str):
        raise NotImplementedError()

    def save_app_password(self, principal_id: str, secret: str):
        raise NotImplementedError()

    def save_email_addresses(self, principal_id: str, emails: str | list[str]):
        raise NotImplementedError()

    def replace_email_addresses(self, principal_id: str, emails: list[tuple[str, str]]):
        raise NotImplementedError()

    def delete_email_addresses(self, principal_id: str, emails: str | list[str]):
        raise NotImplementedError()

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

    def create_domain(self, domain, description=''):
        raise NotImplementedError()

    def delete_domain(self, domain_name: str):
        raise NotImplementedError()

    def get_dns_records(self, domain_name: str) -> list[dict]:
        raise NotImplementedError()

    def get_dkim_signatures(self, domain_name: str) -> list[dict]:
        raise NotImplementedError()

    def get_dkim_dns_records(self, domain_name: str) -> list[dict]:
        raise NotImplementedError()

    def build_expected_dns_records(self, cust_domain: str) -> list[dict]:
        raise NotImplementedError()

    def check_domain_dns(self, domain_name: str) -> dict:
        raise NotImplementedError()
