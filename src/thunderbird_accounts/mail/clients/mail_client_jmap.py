# =====================================================================================
# Stalwart v0.16 JMAP mail client implementation
# -------------------------------------------------------------------------------------
# Stalwart v0.16.13 REMOVED the entire /api/* REST management surface. All management
# CRUD now goes through the JMAP "Registry" API at `POST {STALWART_BASE_API_URL}/jmap`
# using PascalCase object methods (x:Account/*, x:Domain/*, x:DkimSignature/*, ...).
#
# This is the verified end-to-end port (live-validated against Stalwart v0.16.13),
# restructured out of the old single-file `mail/clients.py` into this package. It
# preserves every public method name / signature / return type of the v0.15 client, so
# callers and Celery tasks are unchanged; only the transport (jmap_client.JMAPClient)
# and object shapes change. Purely local DNS logic (build_expected_dns_records /
# check_domain_dns) is carried over as-is.
#
# Design + source-verified shapes: docs/stalwart-v0.16-migration.md
#
# get_account/get_domain/etc. return the v0.15-COMPATIBLE dict (see _account_to_compat),
# NOT a raw pydantic model, so existing callers keep working. Pydantic models
# (stalwart_types) are used only for non-fatal schema-drift validation.
# =====================================================================================

from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from django.conf import settings

from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.clients.mail_client_interface import (
    DkimSignatureStage,
    MailClientInterface,
)
from thunderbird_accounts.mail.clients.stalwart_types import AccountType, DomainType
from thunderbird_accounts.mail.exceptions import (
    AccountNotFoundError,
    DomainNotFoundError,
    FailedToCreateDKIM,
    StalwartError,
)

# JMAP capability set. `urn:stalwart:jmap` is the registry/management capability and is
# exempt from the JMAP `using` check.
JMAP_USING = ['urn:ietf:params:jmap:core', 'urn:stalwart:jmap']

# Map the app's configured DKIM algorithm names (settings.STALWART_DKIM_ALGOS =
# ['Ed25519', 'Rsa']) onto the v0.16 JMAP DkimSignature `@type` discriminators.
DKIM_ALGO_JMAP_TYPES = {
    'Rsa': 'Dkim1RsaSha256',
    'RSA': 'Dkim1RsaSha256',
    'Ed25519': 'Dkim1Ed25519Sha256',
    'ED25519': 'Dkim1Ed25519Sha256',
    # Accept already-mapped values too, in case config is updated later.
    'Dkim1RsaSha256': 'Dkim1RsaSha256',
    'Dkim1Ed25519Sha256': 'Dkim1Ed25519Sha256',
}


class MailClientJMAP(MailClientInterface):
    """A partial api client for Stalwart v0.16.13 (JMAP Registry API).

    v0.16 removed the REST /api/* management surface. All management CRUD goes through
    `POST {STALWART_BASE_API_URL}/jmap`. Objects are addressed by their numeric JMAP
    `id`, so callers that pass a login/domain *name* are resolved to an id first.

    See docs/stalwart-v0.16-migration.md for verified object shapes.
    """

    def __init__(self):
        # Config-driven transport (URL/auth/TLS all from settings — no hardcoded host).
        self.jmap = JMAPClient()

    # ------------------------------------------------------------------ #
    # Error handling
    # ------------------------------------------------------------------ #

    def _raise_for_error(self, response):
        """Parse an RFC7807 problem+json body from a non-JMAP call (e.g. GET /api/account)
        and raise a StalwartError. Best-effort / defensive."""
        try:
            data = response.json()
        except ValueError:
            return
        if not isinstance(data, dict):
            return
        # RFC7807 problem+json shape.
        if data.get('type') or data.get('title') or data.get('detail'):
            detail = data.get('detail') or data.get('title') or data.get('type')
            if detail:
                raise StalwartError(str(detail))

    def _raise_on_set_error(self, arguments: dict, context: str = '') -> None:
        """Raise if a x:*/set response reported per-object failures."""
        for key in ('notCreated', 'notUpdated', 'notDestroyed'):
            errors = arguments.get(key)
            if errors:
                raise StalwartError(f'{context}: {key}: {errors}')

    # ------------------------------------------------------------------ #
    # JMAP transport
    # ------------------------------------------------------------------ #

    def make_jmap_admin_call(self, call: dict) -> dict:
        """POST a fully-formed JMAP request ({using, methodCalls}) to `/jmap` and return
        the parsed response dict (contains `methodResponses`).

        NB: v0.15 posted to `{STALWART_BASE_JMAP_URL}/api`; that path is gone.
        """
        return self.jmap.post(call)

    def _jmap(self, method_calls: list) -> list:
        """Run a list of methodCalls and return the methodResponses list.

        Raises StalwartError on a method-level `["error", {...}, cid]` response.
        """
        response = self.make_jmap_admin_call({'using': JMAP_USING, 'methodCalls': method_calls})
        method_responses = response.get('methodResponses', [])
        for method_name, arguments, _call_id in method_responses:
            if method_name == 'error':
                raise StalwartError(f'Stalwart JMAP error: {arguments}')
        return method_responses

    @staticmethod
    def _find_response(method_responses: list, method_name: str) -> Optional[dict]:
        for name, arguments, _call_id in method_responses:
            if name == method_name:
                return arguments
        return None

    # ------------------------------------------------------------------ #
    # Non-fatal schema-drift validation (uses the typed models internally)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate(model, data: dict, context: str) -> None:
        """Best-effort parse of a raw registry object through its pydantic model to catch
        schema drift. NEVER fatal: callers always receive the raw dict, so a validation
        failure here only logs (and reports to Sentry if available)."""
        try:
            model(**data)
        except Exception as ex:  # ValidationError or anything else — must not break callers
            logging.warning(f'[MailClientJMAP._validate] {context}: object failed {model.__name__} validation: {ex}')
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(ex)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # name -> id resolution
    # ------------------------------------------------------------------ #

    def _resolve_account_id(self, name: str) -> str:
        """Resolve an account login name OR full email to its numeric id.

        x:Account/query only filters by `name` (the login local part); a full-email value
        yields `unsupportedFilter: Filter on property name`. Delegate to _get_account_raw,
        which queries by local part and disambiguates by domainId for emails.
        """
        return self._get_account_raw(name)['id']

    def _resolve_domain_id(self, name: str) -> str:
        """Resolve a domain name to its numeric JMAP id."""
        responses = self._jmap([['x:Domain/query', {'filter': {'name': name}}, 'c0']])
        arguments = self._find_response(responses, 'x:Domain/query')
        ids = (arguments or {}).get('ids') or []
        if not ids:
            raise DomainNotFoundError(name)
        return ids[0]

    def _account_set_update(self, account_id: str, patch: dict, context: str = 'x:Account/set update') -> dict:
        """Apply a JSON-Pointer PatchObject to an account by id."""
        responses = self._jmap([['x:Account/set', {'update': {account_id: patch}}, 'c0']])
        arguments = self._find_response(responses, 'x:Account/set')
        if arguments is None:
            raise StalwartError(f'{context}: no x:Account/set response')
        self._raise_on_set_error(arguments, context)
        return arguments.get('updated') or {}

    # ------------------------------------------------------------------ #
    # Compatibility shaping
    # ------------------------------------------------------------------ #

    @staticmethod
    def _account_to_compat(obj: dict) -> dict:
        """Normalize a v0.16 x:Account object into the v0.15-shaped dict callers still
        expect (`id`, `type`, `description`, `emails`, `secrets`, `quota`, `usedQuota`).
        Raw v0.16 fields are preserved alongside the compat keys.
        """
        compat = dict(obj)

        # emails = primary emailAddress + reconstructed alias addresses.
        # aliases is a VecMap keyed by INDEX ("0","1",...), so its keys are NOT addresses;
        # each value is an EmailAlias {name:<local part>, domainId}. Rebuild the address as
        # <name>@<domain>. We can only cheaply resolve the domain for aliases on the account's
        # own domain (no domainId->name lookup here), so cross-domain aliases are skipped.
        emails: list[str] = []
        primary = obj.get('emailAddress')
        primary_domain = primary.split('@', 1)[1] if primary and '@' in primary else None
        if primary:
            emails.append(primary)
        aliases = obj.get('aliases')
        alias_values = (
            list(aliases.values()) if isinstance(aliases, dict)
            else aliases if isinstance(aliases, list) else []
        )
        account_domain_id = obj.get('domainId')
        for alias in alias_values:
            if isinstance(alias, dict):
                name = alias.get('name')
                if name and primary_domain and alias.get('domainId') == account_domain_id:
                    emails.append(f'{name}@{primary_domain}')
            elif isinstance(alias, str):
                emails.append(alias)

        # secrets = credential `secret` values (credentials is a map keyed "0","1",...)
        secrets: list[str] = []
        credentials = obj.get('credentials')
        cred_values = []
        if isinstance(credentials, dict):
            cred_values = list(credentials.values())
        elif isinstance(credentials, list):
            cred_values = credentials
        for entry in cred_values:
            if isinstance(entry, dict) and entry.get('secret'):
                secrets.append(entry['secret'])
            elif isinstance(entry, str):
                secrets.append(entry)

        # quota: v0.16 `quotas` is a VecMap<StorageQuota,u64> keyed by camelCase enum name;
        # disk bytes live under `maxDiskQuota` (source-verified). `usedDiskQuota` is separate.
        quota = 0
        quotas = obj.get('quotas')
        if isinstance(quotas, dict):
            value = quotas.get('maxDiskQuota')
            if isinstance(value, (int, float)):
                quota = value
        elif isinstance(quotas, (int, float)):
            quota = quotas

        compat['type'] = 'individual'
        compat['id'] = obj.get('id')
        compat['description'] = obj.get('description')
        compat['emails'] = emails
        compat['secrets'] = secrets
        compat['quota'] = quota
        compat['usedQuota'] = obj.get('usedDiskQuota')
        return compat

    # ------------------------------------------------------------------ #
    # Health check
    # ------------------------------------------------------------------ #

    def get_telemetry(self):
        """Health check via the surviving GET /api/account endpoint.

        Returns the token's {permissions, edition, locale}. Used only for /health.
        """
        response = self.jmap.api_get('/account')
        self._raise_for_error(response)
        return response

    def _reload(self):
        """No-op. Registry writes are transactional in v0.16, so the v0.15
        `GET /api/reload/` call has been removed."""
        return None

    # ------------------------------------------------------------------ #
    # Accounts
    # ------------------------------------------------------------------ #

    def _get_account_raw(self, principal_id: str) -> dict:
        """Batched query->get for an account by login name OR full email.

        x:Account/query only filters by `name` (login local part) -- a full email is an
        invalid `name` value. So for an email we query by the local part and disambiguate
        by domainId; for a bare login we query by name directly.
        Raises AccountNotFoundError when no matching account exists (including when the
        caller passes a falsy identifier, e.g. an unprovisioned user's None primary email).
        """
        if not principal_id:
            raise AccountNotFoundError(principal_id)
        if '@' in principal_id:
            local, _, domain = principal_id.partition('@')
            domain_id = self._resolve_domain_id(domain)
        else:
            local, domain_id = principal_id, None
        responses = self._jmap(
            [
                ['x:Account/query', {'filter': {'name': local}}, 'c0'],
                [
                    'x:Account/get',
                    {'#ids': {'resultOf': 'c0', 'name': 'x:Account/query', 'path': '/ids'}},
                    'c1',
                ],
            ]
        )
        arguments = self._find_response(responses, 'x:Account/get')
        account_list = (arguments or {}).get('list') or []
        if domain_id is not None:
            account_list = [a for a in account_list if a.get('domainId') == domain_id]
        if not account_list:
            raise AccountNotFoundError(principal_id)
        account = account_list[0]
        self._validate(AccountType, account, f'get_account({principal_id})')
        return account

    def get_account(self, principal_id: str) -> dict:
        """Fetch an account and return it in the v0.15-compatible shape."""
        obj = self._get_account_raw(principal_id)
        return self._account_to_compat(obj)

    def create_account(
        self,
        emails: list[str],
        principal_id: str,
        full_name: Optional[str] = None,
        app_password: Optional[str] = None,
        quota: Optional[int] = None,
    ):
        """Create an account via x:Account/set create.

        The domain of the primary email must already exist (resolved to a domainId).
        Returns the created account's numeric JMAP id (the "pkid" callers store).
        """
        primary_email = emails[0] if emails else principal_id
        domain_name = primary_email.split('@')[-1]
        domain_id = self._resolve_domain_id(domain_name)

        create_obj: dict = {
            '@type': 'User',
            'name': principal_id,
            'description': full_name,
            'domainId': domain_id,
            # NOTE: emailAddress is server-derived from name@domain and is a "server set
            # property" -- including it fails create with invalidPatch. The primary
            # address comes from `name` (login local part) + `domainId`.
            # roles is a typed object (role preset), NOT a list like the v0.15 ['user'].
            'roles': {'@type': 'User'},
        }

        # Additional addresses become aliases (VecMap<EmailAlias> keyed by index).
        extra_emails = [email for email in emails[1:] if email and email != primary_email]
        if extra_emails:
            create_obj['aliases'] = self._aliases_to_map([self._email_to_alias(e) for e in extra_emails])

        if quota:
            create_obj['quotas'] = {'maxDiskQuota': quota}

        if app_password:
            # Password credential (secret settable); AppPassword.secret is server-generated.
            create_obj['credentials'] = {'0': {'@type': 'Password', 'secret': app_password}}

        responses = self._jmap([['x:Account/set', {'create': {'p0': create_obj}}, 'c0']])
        arguments = self._find_response(responses, 'x:Account/set')
        if arguments is None:
            raise StalwartError('create_account: no x:Account/set response')
        self._raise_on_set_error(arguments, f'create_account {principal_id}')

        created = (arguments.get('created') or {}).get('p0') or {}
        return created.get('id')

    def delete_account(self, principal_id: str):
        """Delete an account via x:Account/set destroy [id]."""
        account_id = self._resolve_account_id(principal_id)
        responses = self._jmap([['x:Account/set', {'destroy': [account_id]}, 'c0']])
        arguments = self._find_response(responses, 'x:Account/set')
        if arguments is None:
            raise StalwartError('delete_account: no x:Account/set response')
        self._raise_on_set_error(arguments, f'delete_account {principal_id}')
        return arguments.get('destroyed') or []

    # ------------------------------------------------------------------ #
    # App passwords (read-modify-write of the credentials map)
    # ------------------------------------------------------------------ #

    def save_app_password(self, principal_id: str, secret: str):
        """Add a Password credential (client-supplied secret).

        JSON-Pointer append (`credentials/<next>`) -- do NOT rewrite the whole credentials
        map: existing entries' secrets are server-set once created, so re-sending them fails
        with 'Cannot modify server set property credentials/secret'. AppPassword.secret is
        server-generated, so a client secret uses a Password credential (secret IS settable),
        matching v0.15 semantics where the `secrets` list held additional login passwords.
        """
        obj = self._get_account_raw(principal_id)
        account_id = obj['id']
        credentials = obj.get('credentials') or {}
        indices = [int(key) for key in credentials.keys() if str(key).isdigit()]
        next_index = (max(indices) + 1) if indices else 0
        self._account_set_update(
            account_id,
            {f'credentials/{next_index}': {'@type': 'Password', 'secret': secret}},
            context='save_app_password',
        )

    def delete_app_password(self, principal_id: str, secret: str):
        """Cannot delete by plaintext secret.

        v0.16 stores credential secrets hashed, so a plaintext secret cannot identify which
        credential to remove (deletion targets a credentialId). The app's (principal_id,
        secret) signature provides only the plaintext, so this is a logged no-op; the proper
        PR should look up the credentialId and set `credentials/<i>` -> null.
        """
        logging.warning(
            'delete_app_password: v0.16 cannot match a credential by plaintext secret '
            '(needs credentialId); no-op'
        )
        return None

    # ------------------------------------------------------------------ #
    # Email addresses / aliases (read-modify-write of the aliases map)
    # ------------------------------------------------------------------ #

    # aliases = VecMap<EmailAlias> -> JSON object keyed by stringified index "0","1",...
    # EmailAlias = {@type:"EmailAlias", name:<LOCAL PART>, domainId:<id>, enabled:bool}.
    # `name` is validated as an email local part (a full email is rejected).
    @staticmethod
    def _clean_alias(alias: dict) -> dict:
        out = {'@type': 'EmailAlias', 'name': alias.get('name'), 'enabled': alias.get('enabled', True)}
        if alias.get('domainId'):
            out['domainId'] = alias['domainId']
        if alias.get('description'):
            out['description'] = alias['description']
        return out

    def _email_to_alias(self, email: str) -> dict:
        local, _, domain = email.partition('@')
        alias = {'@type': 'EmailAlias', 'name': local, 'enabled': True}
        if domain:
            alias['domainId'] = self._resolve_domain_id(domain)
        return alias

    def _existing_aliases(self, obj: dict) -> list[dict]:
        return [self._clean_alias(a) for a in (obj.get('aliases') or {}).values() if isinstance(a, dict)]

    @staticmethod
    def _aliases_to_map(aliases: list[dict]) -> dict:
        return {str(i): a for i, a in enumerate(aliases)}

    @staticmethod
    def _alias_key(alias: dict):
        return (alias.get('name'), alias.get('domainId'))

    @staticmethod
    def _aliases_replace_patch(old_count: int, desired: list[dict]) -> dict:
        """Build a JSON-Pointer PatchObject that replaces the aliases VecMap with `desired`:
        set aliases/0..n-1, then null out any trailing old indices to trim. (Aliases have no
        server-set fields, so re-sending existing ones is safe -- unlike credentials.)"""
        patch = {f'aliases/{i}': alias for i, alias in enumerate(desired)}
        for j in range(len(desired), old_count):
            patch[f'aliases/{j}'] = None
        return patch

    def save_email_addresses(self, principal_id: str, emails: str | list[str]):
        """Add alias addresses via JSON-Pointer append (`aliases/<next>`)."""
        if isinstance(emails, str):
            emails = [emails]
        obj = self._get_account_raw(principal_id)
        account_id = obj['id']
        existing = self._existing_aliases(obj)
        have = {self._alias_key(a) for a in existing}
        primary = obj.get('emailAddress')
        patch: dict = {}
        idx = len(existing)
        for email in emails:
            if not email or email == primary:
                continue
            alias = self._email_to_alias(email)
            if self._alias_key(alias) in have:
                continue
            patch[f'aliases/{idx}'] = alias
            have.add(self._alias_key(alias))
            idx += 1
        if patch:
            self._account_set_update(account_id, patch, context='save_email_addresses')

    def replace_email_addresses(self, principal_id: str, emails: list[tuple[str, str]]):
        """Swap alias addresses (remove old, add new) via pointer replace."""
        obj = self._get_account_raw(principal_id)
        account_id = obj['id']
        existing = self._existing_aliases(obj)
        primary = obj.get('emailAddress')
        desired = list(existing)
        for old_email, new_email in emails:
            old_key = self._alias_key(self._email_to_alias(old_email))
            desired = [a for a in desired if self._alias_key(a) != old_key]
            if new_email and new_email != primary:
                desired.append(self._email_to_alias(new_email))
        self._account_set_update(
            account_id, self._aliases_replace_patch(len(existing), desired), context='replace_email_addresses'
        )

    def delete_email_addresses(self, principal_id: str, emails: str | list[str]):
        """Remove alias addresses by (local part, domainId) via pointer replace."""
        if isinstance(emails, str):
            emails = [emails]
        obj = self._get_account_raw(principal_id)
        account_id = obj['id']
        existing = self._existing_aliases(obj)
        targets = {self._alias_key(self._email_to_alias(email)) for email in emails}
        desired = [a for a in existing if self._alias_key(a) not in targets]
        if len(desired) != len(existing):
            self._account_set_update(
                account_id, self._aliases_replace_patch(len(existing), desired), context='delete_email_addresses'
            )

    # ------------------------------------------------------------------ #
    # Account field updates
    # ------------------------------------------------------------------ #

    def update_individual(
        self,
        principal_id: str,
        primary_email_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ):
        """Update primary email and/or full name via a PatchObject."""
        patch: dict = {}
        if primary_email_address:
            # v0.16: emailAddress is server-derived from name@domain and is a server-set
            # property (cannot be patched directly). Change the login `name` (local part);
            # the server re-derives the primary address. (A cross-domain change would also
            # need domainId, not handled here.)
            patch['name'] = primary_email_address.split('@')[0]
        if full_name:
            patch['description'] = full_name

        if not patch:
            raise ValueError('You must provide at least one field to change.')

        account_id = self._resolve_account_id(principal_id)
        self._account_set_update(account_id, patch, context='update_individual')

    def update_quota(self, principal_id: str, quota: int):
        """Update the account storage quota.

        `quotas` is a VecMap<StorageQuota,u64> serialized as an object keyed by the
        camelCase enum name; the disk-bytes key is `maxDiskQuota` (v0.16.13 source).
        """
        account_id = self._resolve_account_id(principal_id)
        # JSON-Pointer update: target the map key, don't replace the whole quotas map.
        self._account_set_update(account_id, {'quotas/maxDiskQuota': quota}, context='update_quota')

    def make_api_key(self, principal_id, password):
        """BLOCKED.

        API key creation now goes through x:ApiKey/set, which requires the
        `sysApiKeyCreate` permission. The tb-dev fallback-admin token does NOT hold it,
        and this path is dev-only, so it is intentionally not implemented.
        """
        raise NotImplementedError(
            'make_api_key is not supported against Stalwart v0.16: x:ApiKey/set requires '
            'the sysApiKeyCreate permission which the current token lacks. (dev-only path)'
        )

    # ------------------------------------------------------------------ #
    # Domains
    # ------------------------------------------------------------------ #

    def get_domain(self, domain):
        """Fetch a domain by name (batched query->get).

        Returns the raw v0.16 x:Domain object (has `id`, `name`, `dnsZoneFile`, ...).
        """
        responses = self._jmap(
            [
                ['x:Domain/query', {'filter': {'name': domain}}, 'c0'],
                [
                    'x:Domain/get',
                    {'#ids': {'resultOf': 'c0', 'name': 'x:Domain/query', 'path': '/ids'}},
                    'c1',
                ],
            ]
        )
        arguments = self._find_response(responses, 'x:Domain/get')
        domain_list = (arguments or {}).get('list') or []

        logging.info(f'[MailClientJMAP.get_domain({domain})]: {domain_list}')

        if not domain_list:
            raise DomainNotFoundError(domain)
        result = domain_list[0]
        self._validate(DomainType, result, f'get_domain({domain})')
        return result

    def create_domain(self, domain, description=''):
        """Create a domain via x:Domain/set create; returns the domainId.

        NOTE: the v0.16 Domain schema does not clearly expose `description`; it is only
        sent when non-empty and may need to be dropped if the set is rejected.
        """
        create_obj: dict = {'@type': 'Domain', 'name': domain}
        if description:
            create_obj['description'] = description

        responses = self._jmap([['x:Domain/set', {'create': {'d0': create_obj}}, 'c0']])
        arguments = self._find_response(responses, 'x:Domain/set')
        if arguments is None:
            raise StalwartError('create_domain: no x:Domain/set response')
        self._raise_on_set_error(arguments, f'create_domain {domain}')

        created = (arguments.get('created') or {}).get('d0') or {}
        # Return the pkid (domainId)
        return created.get('id')

    def delete_domain(self, domain_name: str):
        """Delete a domain via x:Domain/set destroy [id]."""
        domain_id = self._resolve_domain_id(domain_name)  # raises DomainNotFoundError
        responses = self._jmap([['x:Domain/set', {'destroy': [domain_id]}, 'c0']])
        arguments = self._find_response(responses, 'x:Domain/set')
        if arguments is None:
            raise StalwartError('delete_domain: no x:Domain/set response')
        self._raise_on_set_error(arguments, f'delete_domain {domain_name}')

    # ------------------------------------------------------------------ #
    # DKIM
    # ------------------------------------------------------------------ #

    @staticmethod
    def _generate_dkim_secret(jmap_type: str) -> str:
        """Generate a DKIM private key (PEM) client-side.

        v0.16 does NOT auto-generate the keypair (v0.15 did) — x:DkimSignature/set create
        requires a `secret` (PEM private key). cryptography is imported lazily so module
        import never fails if it is absent.
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

        if jmap_type == 'Dkim1Ed25519Sha256':
            private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pem.decode()

    def create_dkim(self, domain, stage: DkimSignatureStage = DkimSignatureStage.PENDING, algorithms=None):
        """Create DKIM signatures via x:DkimSignature/set create.

        Requires a domainId (resolved) and a client-generated private key per algorithm.
        The v0.15 `_reload` step is gone (registry writes are transactional).
        Returns a list of created signature objects (may be used for testing).
        """
        response_data = []
        dkim_algorithms = settings.STALWART_DKIM_ALGOS if algorithms is None else algorithms
        domain_id = self._resolve_domain_id(domain)

        for algorithm in dkim_algorithms:
            jmap_type = DKIM_ALGO_JMAP_TYPES.get(algorithm) or DKIM_ALGO_JMAP_TYPES.get(str(algorithm).capitalize())
            if not jmap_type:
                raise FailedToCreateDKIM(algorithm, domain, f'Unknown DKIM algorithm {algorithm!r}')

            selector = settings.STALWART_DKIM_ALGO_SELECTORS.get(algorithm)

            try:
                secret = self._generate_dkim_secret(jmap_type)
            except Exception as exc:  # cryptography missing or keygen failure
                raise FailedToCreateDKIM(algorithm, domain, str(exc)) from exc

            create_obj: dict = {
                '@type': jmap_type,
                'domainId': domain_id,
                'selector': selector,
                # privateKey is a SecretText wrapper, not a bare `secret` field.
                'privateKey': {'@type': 'Text', 'secret': secret},
            }
            if settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
                create_obj['stage'] = stage.value

            try:
                responses = self._jmap([['x:DkimSignature/set', {'create': {'k0': create_obj}}, 'c0']])
            except (requests.RequestException, StalwartError) as exc:
                raise FailedToCreateDKIM(algorithm, domain, str(exc)) from exc

            arguments = self._find_response(responses, 'x:DkimSignature/set')
            if arguments is None:
                raise FailedToCreateDKIM(algorithm, domain, 'no x:DkimSignature/set response')
            not_created = arguments.get('notCreated')
            if not_created:
                raise FailedToCreateDKIM(algorithm, domain, str(not_created))

            # _reload removed in v0.16 (no-op / transactional writes).
            created = (arguments.get('created') or {}).get('k0')
            response_data.append(created)

        return response_data

    def delete_dkim(self, domain) -> Optional[list]:
        """Destroy all DKIM signatures for a domain.

        Replaces the v0.15 /api/settings clear. Returns None if there's nothing to
        delete, otherwise the list of destroyed signature ids.
        """
        try:
            domain_id = self._resolve_domain_id(domain)
        except DomainNotFoundError:
            return None

        responses = self._jmap([['x:DkimSignature/query', {'filter': {'domainId': domain_id}}, 'c0']])
        arguments = self._find_response(responses, 'x:DkimSignature/query')
        signature_ids = (arguments or {}).get('ids') or []
        if not signature_ids:
            return None

        responses = self._jmap([['x:DkimSignature/set', {'destroy': signature_ids}, 'c0']])
        arguments = self._find_response(responses, 'x:DkimSignature/set')
        if arguments is None:
            raise StalwartError('delete_dkim: no x:DkimSignature/set response')
        self._raise_on_set_error(arguments, f'delete_dkim {domain}')
        return arguments.get('destroyed') or []

    def get_dkim_signatures(self, domain_name: str) -> list[dict]:
        """Fetch DKIM signatures for a domain via batched x:DkimSignature query->get.

        (Unchanged logic; routes through make_jmap_admin_call, now pointed at /jmap.)
        """
        domain = self.get_domain(domain_name)
        domain_id = domain.get('id')
        if not domain_id:
            raise RuntimeError(f'Stalwart domain {domain_name} did not include an id')

        response = self.make_jmap_admin_call(
            {
                'using': JMAP_USING,
                'methodCalls': [
                    [
                        'x:DkimSignature/query',
                        {'filter': {'domainId': domain_id}},
                        'q',
                    ],
                    [
                        'x:DkimSignature/get',
                        {'#ids': {'resultOf': 'q', 'name': 'x:DkimSignature/query', 'path': '/ids'}},
                        'g',
                    ],
                ],
            }
        )

        for method_name, arguments, _call_id in response.get('methodResponses', []):
            if method_name == 'x:DkimSignature/get':
                return arguments.get('list', [])
            if method_name == 'error':
                raise RuntimeError(f'Stalwart JMAP error fetching DKIM signatures: {arguments}')

        raise RuntimeError('Stalwart JMAP response did not include x:DkimSignature/get')

    def get_dkim_selectors(self, domain_name: str) -> set[str]:
        """Return DKIM selectors already present in Stalwart's DNS records."""
        selectors = set()
        domain_name = domain_name.rstrip('.').lower()
        suffix = f'._domainkey.{domain_name}'

        for record in self.get_dkim_dns_records(domain_name):
            if record.get('type') != 'TXT':
                continue

            record_name = record.get('name', '').rstrip('.').lower()
            if not record_name.endswith(suffix):
                continue

            selector = record_name[: -len(suffix)]
            if selector:
                selectors.add(selector)

        return selectors

    def ensure_dkim(self, domain_name: str, stage: DkimSignatureStage = DkimSignatureStage.PENDING) -> list[dict]:
        """Create only the configured DKIM selectors that are missing."""
        existing_selectors = self.get_dkim_selectors(domain_name)
        missing_algorithms = [
            algorithm
            for algorithm in settings.STALWART_DKIM_ALGOS
            if (settings.STALWART_DKIM_ALGO_SELECTORS.get(algorithm) or '').lower() not in existing_selectors
        ]

        if not missing_algorithms:
            return []

        return self.create_dkim(domain_name, stage=stage, algorithms=missing_algorithms)

    def activate_pending_dkim_signatures(self, domain_name: str) -> list[str]:
        """Activate pending DKIM signatures after their DNS records have been verified.

        (Unchanged logic; routes through make_jmap_admin_call, now pointed at /jmap.)
        """
        if not settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
            return []

        updates = {}
        for signature in self.get_dkim_signatures(domain_name):
            if signature.get('stage') != DkimSignatureStage.PENDING.value:
                continue

            signature_id = signature.get('id')
            if not signature_id:
                raise RuntimeError(f'Pending DKIM signature for {domain_name} did not include an id')

            updates[signature_id] = {'stage': DkimSignatureStage.ACTIVE.value}

        if not updates:
            return []

        response = self.make_jmap_admin_call(
            {
                'using': JMAP_USING,
                'methodCalls': [
                    [
                        'x:DkimSignature/set',
                        {'update': updates},
                        'u',
                    ],
                ],
            }
        )

        for method_name, arguments, _call_id in response.get('methodResponses', []):
            if method_name == 'x:DkimSignature/set':
                if arguments.get('notUpdated'):
                    raise RuntimeError(f'Stalwart failed to activate DKIM signatures: {arguments["notUpdated"]}')

                updated = arguments.get('updated') or {}
                return list(updated.keys()) if isinstance(updated, dict) else updated

            if method_name == 'error':
                raise RuntimeError(f'Stalwart JMAP error activating DKIM signatures: {arguments}')

        raise RuntimeError('Stalwart JMAP response did not include x:DkimSignature/set')

    def get_dkim_dns_records(self, domain_name: str) -> list[dict]:
        if settings.STALWART_DKIM_STAGE_MANAGEMENT_ENABLED:
            try:
                from thunderbird_accounts.mail.dkim import dkim_signatures_to_dns_records

                return dkim_signatures_to_dns_records(domain_name, self.get_dkim_signatures(domain_name))
            except DomainNotFoundError:
                logging.info(f'[MailClientJMAP.get_dkim_dns_records] {domain_name} is not a Stalwart domain yet')
            except Exception as ex:
                logging.warning(f'[MailClientJMAP.get_dkim_dns_records] Falling back to DNS records endpoint: {ex}')

        return [
            record
            for record in self.get_dns_records(domain_name)
            if record.get('type') == 'TXT' and '_domainkey' in record.get('name', '')
        ]

    # ------------------------------------------------------------------ #
    # DNS records (parse the domain's computed BIND zonefile)
    # ------------------------------------------------------------------ #

    def get_dns_records(self, domain_name: str) -> list[dict]:
        """Derive DNS records from the domain's computed `dnsZoneFile`.

        v0.15 exposed GET /api/dns/records/{domain}. v0.16 instead returns a single
        computed BIND zonefile string on the Domain object, which we parse into the
        list-of-dicts ({type, name, content, priority}) the rest of the client expects.
        """
        domain = self.get_domain(domain_name)
        zone_text = domain.get('dnsZoneFile') or ''
        return self._parse_zonefile(zone_text, default_origin=domain_name)

    # --- BIND zonefile parser ---------------------------------------------------- #

    _ZONE_CLASSES = {'IN', 'CH', 'HS', 'CS'}
    _ZONE_TYPES = {
        'A', 'AAAA', 'MX', 'TXT', 'CNAME', 'SRV', 'NS', 'SOA', 'CAA', 'PTR',
        'SPF', 'TLSA', 'DNSKEY', 'DS', 'NAPTR', 'HINFO', 'SVCB', 'HTTPS',
    }
    _ZONE_SKIP_TYPES = {'SOA', 'NS'}
    _ZONE_TTL_RE = re.compile(r'^\d+[smhdwSMHDW]?$')

    @staticmethod
    def _zone_logical_lines(text: str) -> list[str]:
        """Collapse a zonefile into logical records: strip `;` comments, honor quoted
        strings, and join `( ... )` multi-line rdata onto one line."""
        lines: list[str] = []
        buf = ''
        paren = 0
        in_quote = False
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if in_quote:
                buf += ch
                if ch == '"':
                    in_quote = False
                i += 1
                continue
            if ch == '"':
                in_quote = True
                buf += ch
                i += 1
                continue
            if ch == ';':
                # Comment to end of line.
                while i < n and text[i] != '\n':
                    i += 1
                continue
            if ch == '(':
                paren += 1
                buf += ' '
                i += 1
                continue
            if ch == ')':
                paren = max(0, paren - 1)
                buf += ' '
                i += 1
                continue
            if ch == '\n':
                if paren > 0:
                    buf += ' '
                else:
                    if buf.strip():
                        lines.append(buf)
                    buf = ''
                i += 1
                continue
            buf += ch
            i += 1
        if buf.strip():
            lines.append(buf)
        return lines

    @staticmethod
    def _zone_tokenize(line: str) -> list[str]:
        """Split a logical line into tokens; quoted strings are kept as single tokens
        (quotes preserved so TXT rdata can be identified/concatenated)."""
        tokens: list[str] = []
        buf = ''
        in_quote = False
        for ch in line:
            if in_quote:
                buf += ch
                if ch == '"':
                    tokens.append(buf)
                    buf = ''
                    in_quote = False
                continue
            if ch == '"':
                if buf:
                    tokens.append(buf)
                    buf = ''
                buf = '"'
                in_quote = True
                continue
            if ch in ' \t':
                if buf:
                    tokens.append(buf)
                    buf = ''
                continue
            buf += ch
        if buf:
            tokens.append(buf)
        return tokens

    @staticmethod
    def _zone_unquote(token: str) -> str:
        if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
            return token[1:-1]
        return token

    def _parse_zonefile(self, zone_text: str, default_origin: str = '') -> list[dict]:
        """Parse a BIND zonefile string into [{type, name, content, priority}] dicts."""
        records: list[dict] = []
        if not zone_text:
            return records

        origin = ''
        if default_origin:
            origin = default_origin if default_origin.endswith('.') else default_origin + '.'
        last_owner = origin

        def to_fqdn(owner: str) -> str:
            if owner in ('@', ''):
                return origin or '@'
            if owner.endswith('.'):
                return owner
            if origin:
                return f'{owner}.{origin}'
            return f'{owner}.'

        for line in self._zone_logical_lines(zone_text):
            leading_ws = line[:1] in (' ', '\t')
            tokens = self._zone_tokenize(line)
            if not tokens:
                continue

            # Directives
            first_upper = tokens[0].upper()
            if first_upper == '$ORIGIN' and len(tokens) > 1:
                value = tokens[1]
                origin = value if value.endswith('.') else value + '.'
                last_owner = origin
                continue
            if first_upper in ('$TTL', '$INCLUDE', '$GENERATE'):
                continue

            idx = 0
            if leading_ws:
                owner = last_owner
            else:
                owner = tokens[idx]
                idx += 1

            # Skip optional TTL / class tokens, then expect a record type.
            rtype = None
            while idx < len(tokens):
                token = tokens[idx]
                upper = token.upper()
                if upper in self._ZONE_CLASSES:
                    idx += 1
                    continue
                if self._ZONE_TTL_RE.match(token):
                    idx += 1
                    continue
                if upper in self._ZONE_TYPES:
                    rtype = upper
                    idx += 1
                    break
                # Unknown token where a type is expected; treat as the type and stop.
                rtype = upper
                idx += 1
                break

            if rtype is None:
                continue

            last_owner = owner
            if rtype in self._ZONE_SKIP_TYPES:
                continue

            rdata_tokens = tokens[idx:]
            name = to_fqdn(owner)
            priority = '-'

            if rtype == 'TXT' or rtype == 'SPF':
                content = ''.join(self._zone_unquote(token) for token in rdata_tokens)
                record_type = 'TXT'
            elif rtype == 'MX' and len(rdata_tokens) >= 2:
                priority = rdata_tokens[0]
                content = ' '.join(rdata_tokens[1:])
                record_type = 'MX'
            elif rtype == 'SRV' and len(rdata_tokens) >= 4:
                priority = rdata_tokens[0]
                content = ' '.join(rdata_tokens[1:])
                record_type = 'SRV'
            else:
                content = ' '.join(self._zone_unquote(token) for token in rdata_tokens)
                record_type = rtype

            records.append(
                {
                    'type': record_type,
                    'name': name,
                    'content': content,
                    'priority': priority,
                }
            )

        return records

    # ------------------------------------------------------------------ #
    # Local DNS logic (unchanged; does not call Stalwart)
    # ------------------------------------------------------------------ #

    def build_expected_dns_records(self, cust_domain: str) -> list[dict]:
        """Build the full list of DNS records the user must configure for a customer domain."""
        from thunderbird_accounts.mail.dkim import build_customer_dkim_cname_records

        target_domain = settings.CONNECTION_INFO['SMTP']['HOST'].rstrip('.')
        target_domain_fqdn = f'{target_domain}.'
        target_top_domain = '.'.join(target_domain.split('.')[1:])
        normalized_cust_domain = cust_domain.rstrip('.')
        mx_name = '@' if len(normalized_cust_domain.split('.')) == 2 else f'{normalized_cust_domain}.'

        records = [
            {'type': 'MX', 'name': mx_name, 'content': target_domain_fqdn, 'priority': '10'},
            {
                'type': 'SRV',
                'name': f'_jmap._tcp.{normalized_cust_domain}.',
                'content': f'1 443 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_caldavs._tcp.{normalized_cust_domain}.',
                'content': f'1 443 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_carddavs._tcp.{normalized_cust_domain}.',
                'content': f'1 443 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_imaps._tcp.{normalized_cust_domain}.',
                'content': f'1 993 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'SRV',
                'name': f'_submission._tcp.{normalized_cust_domain}.',
                'content': f'1 587 {target_domain}',
                'priority': '0',
            },
            {
                'type': 'TXT',
                'name': f'{normalized_cust_domain}.',
                'content': f'v=spf1 include:spf.{target_top_domain} -all',
                'priority': '-',
            },
            {
                'type': 'TXT',
                'name': f'_mta-sts.{normalized_cust_domain}.',
                'content': 'v=STSv1; id=18139500144460329770',
                'priority': '-',
            },
            {
                'type': 'TXT',
                'name': f'_smtp._tls.{normalized_cust_domain}.',
                'content': f'v=TLSRPTv1; rua=mailto:postmaster@{normalized_cust_domain}',
                'priority': '-',
            },
            {
                'type': 'TXT',
                'name': f'_dmarc.{normalized_cust_domain}.',
                'content': 'v=DMARC1; p=none;',
                'priority': '-',
            },
        ]

        records.extend(build_customer_dkim_cname_records(normalized_cust_domain))
        return records

    def check_domain_dns(self, domain_name: str) -> dict:
        """Check expected DNS records and return verification details for a custom domain."""
        # Circular import, so we import here
        from thunderbird_accounts.mail.dns import enrich_dns_records_with_status
        from thunderbird_accounts.mail.clients.mail_client_interface import (
            DNSRecordStatus,
            DomainVerificationErrors,
        )

        expected_records = self.build_expected_dns_records(domain_name)
        dns_records = enrich_dns_records_with_status(domain_name, expected_records)
        critical_errors = []
        warnings = []

        mx_records = [record for record in dns_records if record.get('type') == 'MX']
        if not any(record.get('status') == DNSRecordStatus.MATCH.value for record in mx_records):
            critical_errors.append(DomainVerificationErrors.MX_LOOKUP_ERROR)

        spf_records = [
            record
            for record in dns_records
            if record.get('type') == 'TXT' and record.get('content', '').startswith('v=spf1')
        ]
        if not any(record.get('status') == DNSRecordStatus.MATCH.value for record in spf_records):
            warnings.append(DomainVerificationErrors.SPF_RECORD_NOT_FOUND)

        dkim_records = [record for record in dns_records if '_domainkey' in record.get('name', '')]
        if not dkim_records or any(record.get('status') != DNSRecordStatus.MATCH.value for record in dkim_records):
            critical_errors.append(DomainVerificationErrors.DKIM_RECORD_NOT_FOUND)

        is_verified = len(critical_errors) == 0
        return {
            'is_verified': is_verified,
            'critical_errors': critical_errors,
            'warnings': warnings,
            'dns_records': dns_records,
        }
