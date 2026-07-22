# =====================================================================================
# thunderbird_accounts.mail.clients
# -------------------------------------------------------------------------------------
# Package replacing the old single-file `mail/clients.py`. It re-exports every public
# name the old module exposed so existing imports keep working unchanged:
#
#   from thunderbird_accounts.mail.clients import (
#       MailClient, StalwartErrors, DkimSignatureStage,
#       DomainVerificationErrors, DNSRecordStatus, StaleDNSRecordCode,
#   )
#
# `MailClient` is bound to the Stalwart v0.16 JMAP implementation (`MailClientJMAP`).
# =====================================================================================

from __future__ import annotations

from thunderbird_accounts.mail.clients.mail_client_interface import (
    DkimSignatureStage,
    DNSRecordStatus,
    DomainVerificationErrors,
    MailClientInterface,
    StalwartErrors,
    StaleDNSRecordCode,
)
from thunderbird_accounts.mail.clients.mail_client_jmap import MailClientJMAP
from thunderbird_accounts.mail.clients.mail_client_legacy import MailClientLegacy

# Public alias: callers/tests use `MailClient` and patch methods on it
# (e.g. @patch.object(MailClient, 'make_jmap_admin_call')). Bind it to the JMAP impl.
MailClient = MailClientJMAP

__all__ = [
    'MailClient',
    'MailClientJMAP',
    'MailClientLegacy',
    'MailClientInterface',
    'StalwartErrors',
    'DkimSignatureStage',
    'DomainVerificationErrors',
    'DNSRecordStatus',
    'StaleDNSRecordCode',
]
