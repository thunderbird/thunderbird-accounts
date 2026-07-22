# =====================================================================================
# JMAP transport for Stalwart v0.16
# -------------------------------------------------------------------------------------
# Config-driven HTTP transport for the Stalwart JMAP Registry API. This is the ONLY
# place that talks to the network; the mail client builds JMAP method-call payloads and
# hands them here.
#
# Fixed vs PR #1131's WIP transport:
#   * config-driven URL: `settings.STALWART_BASE_API_URL` + `/jmap` (no hardcoded
#     `http://localhost:8080`), `/api` for the surviving health probe.
#   * config-driven auth: `settings.STALWART_API_AUTH_METHOD` / `STALWART_API_AUTH_STRING`
#     (no hardcoded `admin`/`admin`).
#   * `verify=settings.VERIFY_PRIVATE_LINK_SSL` on every request (was hardcoded
#     `verify=False`).
#   * no `print(...)` debug logging.
# =====================================================================================

from __future__ import annotations

from typing import Optional

import requests
from django.conf import settings


class JMAPClient:
    """Config-driven transport to the Stalwart v0.16 JMAP registry endpoint.

    v0.16 removed the REST `/api/*` management surface: management CRUD POSTs to
    `{STALWART_BASE_API_URL}/jmap`. `/api` survives only for the `GET /api/account`
    health probe.
    """

    def __init__(self):
        base = settings.STALWART_BASE_API_URL
        # Registry endpoint lives on the same host as the API URL.
        self.jmap_url = f'{base}/jmap'
        # /api is kept only for the surviving GET /api/account health probe.
        self.api_url = f'{base}/api'
        self.auth_method = settings.STALWART_API_AUTH_METHOD
        self.auth_string = settings.STALWART_API_AUTH_STRING

        # Sanity check
        assert self.auth_method in ('basic', 'bearer')

        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'{self.auth_method} {self.auth_string}',
        }

        # JMAP session discovery cache (see get_session / get_account_id).
        self._session: Optional[dict] = None
        self._account_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Core transport
    # ------------------------------------------------------------------ #

    def post(self, payload: dict) -> dict:
        """POST a fully-formed JMAP request ({using, methodCalls}) to `/jmap` and return
        the parsed response dict (contains `methodResponses`)."""
        response = requests.post(
            self.jmap_url,
            json=payload,
            headers=self.headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        return response.json()

    def api_get(self, path: str) -> requests.Response:
        """GET a surviving `/api/*` endpoint (only the health probe today)."""
        response = requests.get(
            f'{self.api_url}{path}',
            headers=self.headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
        )
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------ #
    # JMAP session discovery (optional)
    # ------------------------------------------------------------------ #

    def get_session(self) -> dict:
        """Fetch (and cache) the JMAP Session Resource from `/.well-known/jmap`.

        The Stalwart registry methods used by the mail client do not require an
        `accountId`, so this is not on the hot path; it is provided for callers that
        want to resolve the primary account id.
        """
        if self._session is not None:
            return self._session
        response = requests.get(
            f'{settings.STALWART_BASE_API_URL}/.well-known/jmap',
            headers=self.headers,
            verify=settings.VERIFY_PRIVATE_LINK_SSL,
            allow_redirects=True,
        )
        response.raise_for_status()
        self._session = response.json()
        return self._session

    def get_account_id(self) -> Optional[str]:
        """Resolve the primary account id from the session's
        `primaryAccounts['urn:stalwart:jmap']`, falling back to the first account key."""
        if self._account_id is not None:
            return self._account_id
        session = self.get_session()
        account_id = (session.get('primaryAccounts') or {}).get('urn:stalwart:jmap')
        if not account_id:
            accounts = list((session.get('accounts') or {}).keys())
            account_id = accounts[0] if accounts else None
        self._account_id = account_id
        return account_id
