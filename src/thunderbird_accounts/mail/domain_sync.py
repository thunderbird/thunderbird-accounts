from dataclasses import dataclass

from django.conf import settings

from thunderbird_accounts.mail.models import Domain


@dataclass(frozen=True)
class DomainSyncCounts:
    """How the domains in Accounts and in Stalwart line up.

    ``verified``, ``pending`` and ``failed`` are the domains present in both systems, by Accounts status.
    """

    accounts: int
    stalwart: int
    verified: int
    pending: int
    failed: int
    stalwart_only: int
    verified_missing: int


def _normalize(name: str) -> str:
    """Return the ASCII form Stalwart stores."""
    name = name.lower()
    try:
        return name.encode('idna').decode('ascii')
    except UnicodeError:
        return name


def count_domain_sync(stalwart_domain_names: set[str]) -> DomainSyncCounts:
    stalwart_names = {_normalize(name) for name in stalwart_domain_names}
    accounts_status = {_normalize(name): status for name, status in Domain.objects.values_list('name', 'status')}
    service_names = {_normalize(name) for name in settings.ALLOWED_EMAIL_DOMAINS}

    def in_both(status: Domain.DomainStatus) -> int:
        return sum(1 for name in stalwart_names if accounts_status.get(name) == status)

    return DomainSyncCounts(
        accounts=len(accounts_status),
        stalwart=len(stalwart_names),
        verified=in_both(Domain.DomainStatus.VERIFIED),
        pending=in_both(Domain.DomainStatus.PENDING),
        failed=in_both(Domain.DomainStatus.FAILED),
        stalwart_only=len(stalwart_names - accounts_status.keys() - service_names),
        verified_missing=sum(
            1
            for name, status in accounts_status.items()
            if status == Domain.DomainStatus.VERIFIED and name not in stalwart_names
        ),
    )
