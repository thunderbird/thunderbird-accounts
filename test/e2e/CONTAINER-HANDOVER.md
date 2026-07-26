# Handover: Build the thunderbird-accounts e2e test-runner container

**Audience:** an engineer/agent building a containerized Playwright runner. Assume **no prior context** — everything you need is below.

**Owning repo:** `thunderbird/thunderbird-accounts` (the app + `test/e2e` live here; CI publishes images here).

---

## 1. Why this container exists

Thunderbird Pro Accounts deploys to EKS via a **Kargo** promotion pipeline: `merge → build image → auto-deploy tb-dev → VERIFY → (human-authorized) promote to tb-prod`. The **verify** step is a Kubernetes **Job** that runs the e2e suite against the just-deployed tb-dev instance. Its **exit code is the gate**: exit 0 ⇒ the release Freight becomes `verifiedIn[tb-dev]` and is eligible for prod promotion; non-zero ⇒ **fail-closed**, not promotable.

This container **is** that Job's image. Two consumers (build one runner that serves both):

- **P3 — keycloak OIDC gate (priority / first target).** A multi-hop OIDC round-trip against the tb-dev customer-auth Keycloak (`https://auth.tb-dev.thunderbird.dev`, realm `tbpro`): `authorize → token → userinfo → jwks → refresh`. Runs as an Argo Rollouts **`job` metric** (Kargo Stage `verification`). The issuer is public/edge-reachable.
- **P4 — accounts backend smoke (follow-up).** A fast subset: app `health`, core API, a Celery round-trip, migration sanity — run against the freshly-rolled preview Service as a Rollout `prePromotionAnalysis`. **Must run on linux/arm64** (the EKS nodes are Graviton).

You build the **runner image + its publish workflow + the test-subset wiring**. You do **not** build the Kargo/Argo glue (see §7).

---

## 2. Current e2e reality (what you're starting from)

In `thunderbird/thunderbird-accounts`, path `test/e2e/`:

- **Playwright + TypeScript.** `@playwright/test` **`1.59.1`**, `browserstack-node-sdk` `1.52.3` (`test/e2e/package.json`, `name: "e2e"`).
- `playwright.config.ts`: `testDir: ./tests`, `retries: process.env.CI ? 1 : 0`, `trace: 'off'` (comment: *traces can contain sensitive info*), `projects: [...]` for major browsers.
- Structure: `tests/` (e.g. `tests/common/sign-up.spec.ts`), `pages/` page-objects incl. **`pages/tb-accts-oidc-page.ts`** (OIDC flows already modeled), `tb-accts-hub-page.ts`, `dashboard-page.ts`, `mail-page.ts`; `const/constants.ts`, `const/types.ts`, `const/mocks/paddle.ts`; env templates **`.env.dev.example` / `.env.stage.example` / `.env.prod.example`**.
- Tests are selected by **`--grep <tag>` + `--project <browser>`**. Existing tags: `e2e-suite`, `e2e-mobile-suite`, `e2e-prod-desktop-nightly`, `prod-mobile-nightly`. A **local (non-BrowserStack)** path already works: `npm run e2e-test` = `npx playwright test --grep e2e-suite --project=firefox`.
- Today the CI/nightly suites run on **BrowserStack** (`browserstack-node-sdk`, `browserstack-*.yml`). **The gate must NOT use BrowserStack** — it runs **headless chromium locally in the container**.

**Important:** the app image Dockerfile does **not** COPY `test/` — tests are not shipped in the app image, and **no versioned e2e image exists today**. You are creating the first one.

---

## 3. Hard requirements

1. **Multi-arch, including `linux/arm64`.** The accounts smoke (P4) runs on Graviton nodes; the OIDC gate (P3) can run on either. Build with `docker buildx` for `linux/amd64,linux/arm64`.
2. **Headless chromium, local** (not BrowserStack). Add/confirm a `chromium` project in `playwright.config.ts` with `headless: true`.
3. **Version-pinned to the deployed commit.** The gate must run the suite from the **exact git SHA that built the deployed image** (API/schema/feature parity; preserves "tested == promoted"). The SHA is provided to the Job by the caller as env (`GIT_SHA`) — the Kargo step resolves it via `commitFrom(...).ID` (see §5 caveat). If you go with the CI-published-per-SHA image (recommended, §6), the image *is* the version and `GIT_SHA` is just an assertion/label.
4. **Exit-code contract.** Exit `0` = all selected tests passed; any non-zero = fail. No "soft" passes. The Rollouts `job` metric keys purely on Job success/failure.
5. **Subset selection.** Support running a named subset via grep tag. **Dependency (app-team):** two subsets must be added to `test/e2e` and do **not exist yet**:
   - `@oidc` — the headless-chromium (or API-only, see §8) OIDC round-trip against a remote issuer. Leverage `pages/tb-accts-oidc-page.ts`.
   - `@smoke` — arm64 backend-integration subset (health, core API, celery round-trip, migration sanity), fast + deterministic (NOT the full BrowserStack suite).
6. **Fast + deterministic** for the smoke subset (it blocks promotions). Set `retries: 1–2` for the gate; Job `backoffLimit: 0`; a bounded `activeDeadlineSeconds`.

---

## 4. Config / secret interface (env-driven — never bake secrets)

The Job injects env from a Kubernetes Secret (`mzla/tb-dev/accounts-e2e`, synced from AWS Secrets Manager by External Secrets). Your container **reads env only**. Derive the **exact** variable names from `test/e2e/.env.dev.example` + `const/constants.ts`; at minimum expect:

- `ACCTS_HUB_URL` — base URL of the deployed accounts instance (tb-dev: `https://accounts.tb-dev.thunderbird.dev`).
- Keycloak: realm/issuer URL (`https://auth.tb-dev.thunderbird.dev/realms/tbpro`), OIDC client id/secret, admin client id/secret.
- A **dedicated** TB Pro / Keycloak **test user** (email / password / recovery) — never a real user.
- **Paddle SANDBOX** creds (not live).
- `GIT_SHA` — the deployed commit (assert the checked-out/baked tests match).
- `S3_TRACE_BUCKET` (+ region) — where to upload evidence (§6). IRSA on the Job SA grants `s3:PutObject`.
- Neon per-run branch creds/URL (if the test seeds/inspects DB) — the caller creates/deletes the branch.

Document every var you consume in the image README.

---

## 5. How the version SHA reaches the tests (read this — it's a footgun)

- Inside a **Kargo promotion/verification step**, `${{ commitFrom("https://github.com/thunderbird/thunderbird-accounts.git").ID }}` resolves the Freight-pinned commit. The caller passes that value into the Job as `GIT_SHA` (env) or, for P4, writes it into a ConfigMap the Rollout mounts.
- **`commitFrom()` does NOT resolve inside an Argo Rollouts `AnalysisTemplate`** (Rollouts uses `{{ }}` and has no Freight context). So the SHA must arrive as a plain value the caller injected — your container must **not** assume it can resolve the Freight itself.
- Two ways your container can honor the SHA: (a) it was **built at that SHA** (CI publishes `…-e2e:<sha>`, recommended) so the tests are already correct and `GIT_SHA` is a sanity assert; or (b) a generic runner **git-checks-out `$GIT_SHA`** then `npm ci` at start (slower, network-dependent).

---

## 6. Packaging — recommendation + trade-offs

**Recommended: (b) a purpose-built, per-SHA image published by CI → `ghcr.io/thunderbird/thunderbird-accounts-e2e:<sha>`.**

- Base on **`mcr.microsoft.com/playwright:v1.59.1`** (matches `@playwright/test 1.59.1` — pin exactly to avoid browser/driver drift; bump in lockstep with `test/e2e/package.json`).
- Dockerfile: `COPY test/e2e/` → `npm ci` → (browsers already in base image) → entrypoint runs `npx playwright test --grep "$TEST_GREP" --project=chromium`. Multi-arch `buildx` (`linux/amd64,linux/arm64`); tag `:<sha>` (+ optionally `:latest` for humans).
- CI: add a job to the existing publish workflow (runs on the same commit that builds the app images) that `buildx build --push` the e2e image for both arches. Public GHCR package (or grant the cluster pull access).

Trade-offs of the alternatives:
- **(a) generic `mcr…/playwright` + runtime git-clone + `npm ci`** — no new CI image, but slow, network-dependent (npm + git at gate time), and risks tight `activeDeadlineSeconds`. Acceptable for a first spike of P3 only.
- **(c) reuse an in-app-image smoke entrypoint** — the tests aren't in the app image and it's Python, not Node/Playwright; rejected.

---

## 7. Scope boundaries

**IN scope (you build):**
- [ ] The runner **image** (Dockerfile + entrypoint) — multi-arch, headless chromium, env-driven, exit-code gate.
- [ ] Its **CI publish workflow** (`ghcr.io/thunderbird/thunderbird-accounts-e2e:<sha>`, arm64+amd64).
- [ ] The **`@oidc`** and **`@smoke`** subset tags/greps in `test/e2e` (+ a local `chromium` headless project) — coordinate with whoever owns the test specs.
- [ ] Evidence upload (Playwright HTML report/trace → S3 keyed by `<sha>`; mind that traces can hold sensitive data).
- [ ] A local `docker run` smoke against tb-dev proving the image passes/fails correctly.

**OUT of scope (owned by platform-infra / already designed — you only need to match their interface):**
- Kargo `AnalysisTemplate` + Stage `spec.verification` block.
- Warehouse git-subscription + the CI `kargo create -f freight.yaml` workflow (note: it is **`kargo create -f <file>`**; there is **no** `kargo create freight` subcommand in Kargo v1.10.x).
- The `mzla/tb-dev/accounts-e2e` ExternalSecret + IRSA + Neon per-run branching.
- The accounts `Deployment → Rollout` conversion (for P4).

---

## 8. Acceptance criteria

- [ ] `docker buildx` produces a `linux/amd64` **and** `linux/arm64` manifest for `…-e2e:<sha>`.
- [ ] `docker run -e ACCTS_HUB_URL=… -e <keycloak/test-user envs> … …-e2e:<sha>` with `TEST_GREP=@oidc` **exits 0** against a healthy tb-dev and **non-zero** when the OIDC client is broken (prove fail-closed).
- [ ] Same for `TEST_GREP=@smoke` on arm64.
- [ ] No secrets baked into the image; all config via env.
- [ ] Playwright/browser versions pinned and matched to `test/e2e/package.json`.
- [ ] Evidence (report/trace) lands in S3 under a `<sha>` key.
- [ ] Runtime for `@smoke` is bounded well under the Job `activeDeadlineSeconds` the caller will set (target: minutes, not tens of minutes).

## Open decisions (resolve or escalate)

- **Runner packaging:** confirm (b) per-SHA CI image vs (a) generic + runtime clone. (Recommend (b).)
- **OIDC leg shape:** real headless-chromium browser flow (reuses `tb-accts-oidc-page.ts`) vs an **API-only** round-trip (curl/fetch `authorize→token→userinfo→jwks`). API-only is faster/more deterministic for a gate; browser flow catches more. Pick per reliability need.
- **Browser/driver pinning:** exact `mcr.microsoft.com/playwright` tag and how it's kept in lockstep with `@playwright/test` on version bumps.
- **How `GIT_SHA` is delivered** for P4 (ConfigMap written by the Kargo step vs OCI-label derivation) — confirm with platform-infra so the container reads the agreed source.
- **Neon usage:** does the smoke need a seeded per-run DB branch, or is read-only against the shared tb-dev DB sufficient?

---

### Appendix — pointers
- App/tests repo: `github.com/thunderbird/thunderbird-accounts`, `test/e2e/` (`playwright.config.ts`, `tests/`, `pages/tb-accts-oidc-page.ts`, `.env.dev.example`, `package.json`).
- tb-dev targets: accounts `https://accounts.tb-dev.thunderbird.dev`, Keycloak `https://auth.tb-dev.thunderbird.dev` realm `tbpro`.
- Full pipeline design (context, not required reading): `platform-infrastructure` `docs/superpowers/specs/2026-07-08-accounts-cicd-promotion-pipeline-design-v4.md` (§A build, §B verification, §C GitHub release, §D release-driven prod promotion).
