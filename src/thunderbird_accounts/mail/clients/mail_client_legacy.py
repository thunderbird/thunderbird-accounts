# =====================================================================================
# Legacy (Stalwart v0.15) mail client — reference stub
# -------------------------------------------------------------------------------------
# Stalwart v0.16.13 removed the entire REST `/api/*` management surface the v0.15 client
# relied on (`/api/principal`, `/api/dkim`, `/api/settings`, `/api/dns/records`,
# `/api/reload`, ...). The live client is `MailClientJMAP`.
#
# This stub is retained so the `MailClientInterface` stays satisfiable by a v0.15-style
# implementation for reference / potential dual-run. It intentionally does not implement
# the REST calls (they 404 against v0.16); each inherited method raises NotImplementedError
# via the base interface. If a real dual-run is needed, restore the pre-v0.16 REST bodies
# here from git history (`git show 3725b04:.../mail/clients.py` predates the JMAP port).
# =====================================================================================

from __future__ import annotations

from thunderbird_accounts.mail.clients.mail_client_interface import MailClientInterface


class MailClientLegacy(MailClientInterface):
    """Stalwart v0.15 REST management client (removed upstream in v0.16.13).

    Kept as a reference placeholder; all methods inherit the base
    ``NotImplementedError`` behaviour. Use ``MailClientJMAP`` against v0.16 servers.
    """

    def __init__(self):
        # No transport is wired: the v0.15 REST surface no longer exists on v0.16 hosts.
        pass
