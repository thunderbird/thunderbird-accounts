# Stalwart v0.16 migration — `mail/clients.py` port (DRAFT — needs review)

> **Status:** Draft for human review. The `clients.py` rewrite in this PR has been
> validated end-to-end against a **live Stalwart v0.16.13**, but it was developed by
> live-porting on a dev cluster (tb-dev), not through the normal test/dev loop. Please
> review the JMAP shapes, the compatibility layer, and the **Open items** below before
> merging. Do **not** merge without a maintainer pass.

## TL;DR

Stalwart **v0.16.13 removed the entire `/api/*` REST management API** the v0.15 client
depends on. `/api` now serves only `auth / discover / account / schema / token / live`;
**all management CRUD moved to a JMAP "Registry" API** at `POST {host}/jmap` using
PascalCase object methods: `x:Account/*`, `x:Domain/*`, `x:DkimSignature/*`,
`x:ApiKey/*`, `x:AppPassword/*` (capability `urn:stalwart:jmap`).

This PR reimplements every Stalwart-touching method in `clients.py` against that JMAP
API while **preserving all public method names, signatures, and return types**, so
callers and Celery tasks are unchanged. Local-only DNS logic is carried over untouched.

## Why (the breaking changes)

1. **No REST management surface** — `/api/principal`, `/api/dkim`, `/api/settings`,
   `/api/dns/records`, `/api/telemetry/metrics`, `/api/reload` all 404. Verified against
   the v0.16.13 source (`crates/http` routing) and the OpenAPI spec.
2. **Numeric JMAP ids, not names** — objects are addressed by numeric JMAP id. Every CRUD
   needs a name→id resolve step (`x:Account/query` / `x:Domain/query`, or a batched
   `query`→`get`/`set` via a `#ids` result reference).
3. **`x:Account/query` filters only by `name` (login local-part)** — a full-email `name`
   value returns `unsupportedFilter`. There is **no `email` filter**. Resolving a full
   email = query by local part + disambiguate by `domainId`.
4. **Reshaped objects** (source-verified against `crates/registry`):
   - `aliases`: `VecMap<EmailAlias>` → JSON object keyed by stringified index (`"0"`).
     `EmailAlias = {"@type":"EmailAlias","name":<local part>,"domainId":<id>,"enabled":bool}`.
   - `quotas`: `VecMap<StorageQuota,u64>` → object keyed by camelCase enum name;
     disk-bytes key is **`maxDiskQuota`**.
   - `credentials`: `VecMap<Credential>` keyed by index; each
     `{"@type":"Password"|"AppPassword"|"ApiKey","secret":...,"credentialId":...}`.
     `secret` is settable on **Password**; server-set on AppPassword/ApiKey.
   - `roles`: a typed object `{"@type":"User"}` (not a list).
   - `emailAddress` is **server-derived** from `name`@`domain` — cannot be set on create/update.
   - DNS: a single computed `dnsZoneFile` (BIND string) on the Domain — parsed into the
     `{type,name,content}` dicts the rest of the client expects.
   - DKIM: `x:DkimSignature/set` create requires a client-generated key in a SecretText
     wrapper `{"privateKey":{"@type":"Text","secret":"<PKCS8 PEM>"}}`; `@type` ∈
     `Dkim1RsaSha256` / `Dkim1Ed25519Sha256`. v0.16 does **not** auto-generate the keypair.
5. **Updates are JSON-Pointer PatchObjects** — `x:Account/set` update targets `aliases/<i>`,
   `quotas/maxDiskQuota`, `credentials/<i>` etc.; you must **not** replace the whole
   collection map (that yields `invalidPatch: Invalid key`, and re-sending existing
   credentials trips `Cannot modify server set property credentials/secret`). Create paths
   send the whole object (create accepts it).
6. **No `_reload`** — registry writes are transactional; the v0.15 reload step is removed.
7. **Envelope gone** — success is JMAP `methodResponses`; per-object failures are
   `notCreated/notUpdated/notDestroyed` maps of `SetError`; the old `{data}`/`{error}`
   envelope + `StalwartErrors` code set no longer apply.

## What changed in `clients.py`

New helpers: `_jmap()` (POST `/jmap`, parse methodResponses, raise on `["error",…]`),
`_resolve_account_id()` / `_resolve_domain_id()`, `_get_account_raw()` (email→local-part
+domainId), `_account_to_compat()` (maps the v0.16 object back to the v0.15 dict shape —
`emails`, `secrets`, `quota`, `usedQuota`, `id`, `type` — so existing callers keep working),
`_generate_dkim_secret()` (client-side RSA/Ed25519 keygen via `cryptography`), and a BIND
zonefile parser for `get_dns_records`.

Per-method mapping: see the `# v0.16 JMAP port` comments in the module. `get_telemetry`
(health probe) → `GET /api/account` (a surviving endpoint). `make_jmap_admin_call`,
`get_dkim_signatures`, `activate_pending_dkim_signatures` were already JMAP; they now POST
to `/jmap` and parse `methodResponses`.

## Validation (live, tb-dev, Stalwart v0.16.13)

Exercised through the app (`manage.py shell`) against a live instance:

- `/health` all green; `get_domain`, `get_dns_records` (zonefile → 30 records), `get_dkim_signatures`
- account **create → read → update → delete** (full lifecycle)
- `save_email_addresses` (aliases), `update_quota` (`maxDiskQuota`), `save_app_password`
- `create_domain` / `delete_domain`
- **`create_dkim`** — client-generated RSA + Ed25519 keypairs, created + deleted
- subscription plan-info endpoint (`get_account(full_email)`) → `200`
- alias add→delete: `save_email_addresses(2)` then `delete_email_addresses(1)` correctly
  rebuilds the aliases VecMap (verified against raw Stalwart state)

### Review pass (50-lens) — fixes applied
- `_get_account_raw(None)` guarded → raises `AccountNotFoundError` instead of `TypeError`
  (an unprovisioned user's `stalwart_primary_email` is `None`).
- `_account_to_compat` `emails` now reconstructs alias addresses from the `EmailAlias`
  values (`name`@`domain`) instead of the VecMap **index** keys (`"0"`,`"1"`). Cross-domain
  aliases are skipped (no cheap domainId→name lookup in the shaper).
- `_account_to_compat` `quota` now reads `quotas["maxDiskQuota"]` directly (source-verified)
  rather than a heuristic scan.

## Open items — REVIEW / FOLLOW-UP (intentionally not in this PR)

1. **`delete_app_password(principal_id, secret)`** is a **no-op** — v0.16 stores secrets
   hashed, so a plaintext secret can't identify the credential; deletion must target a
   `credentialId` (`credentials/<i>` → null). The signature needs to change or a lookup added.
2. **`create_stalwart_account` (`mail/tasks.py`)** passes the **full email as the Stalwart
   principal `name`** and re-adds the primary email as an alias. v0.16 wants a local-part
   `name` + `domainId`. Needs a consistent identifier-normalization pass (a `_split_identifier`
   helper) — not addressed here.
3. **`TinyJMAPClient` (`mail/tiny_jmap_client.py`)** — the archives-folder middleware uses a
   *separate* JMAP client that (a) reads `settings.STALWART_BASE_JMAP_URL` (must be set), and
   (b) does not honor `VERIFY_PRIVATE_LINK_SSL` (TLS-name mismatch on internal hosts). Needs
   the same treatment as `clients.py`.
4. **Subscription plan-info view** (`subscription/views.py`) returns **500** when a mailbox
   is missing even though used-quota is "optional" — should degrade gracefully.
5. **`cryptography`** is required at runtime for `create_dkim` (imported lazily). Confirm it's
   a declared dependency.
6. **`_account_to_compat` `emails`** reconstructs only *same-domain* aliases (the shaper has
   no domainId→name lookup). If multi-domain aliases must appear in `emails`, add a domain
   cache/lookup. `secrets` returns the server-stored (hashed/masked) credential secrets, not
   plaintext — confirm no caller relies on plaintext.

## Deployment note

`STALWART_BASE_API_URL` must point at the Stalwart host (the client appends `/api` for the
health probe and `/jmap` for the registry). `STALWART_BASE_JMAP_URL` must be set for
`TinyJMAPClient` (item 3). `VERIFY_PRIVATE_LINK_SSL=false` is appropriate when reaching an
internal ClusterIP whose TLS cert is for the public mail host.
