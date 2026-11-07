---
name: dependency-remediation
description: Careful remediation of Dependabot findings across the npm (root and test/e2e) and uv (pyproject.toml) manifests. Prefers in-range re-resolution and parent upgrades over overrides, reads changelogs, checks reachability and test coverage, applies a 7-day cooling period by hand, surfaces high-risk findings without a clean fix for a human decision, and produces a routine PR plus one gated PR per decision that needs review, each with a QA Log. Run manually from a laptop.
---

# Dependency audit remediation

Policy lives in `docs/dependency-remediation.md`; this file is the procedure. The primary
metric is **open Dependabot alerts**, not the `npm audit` count.

There is no committed decision log. Two places hold the record: Dependabot keeps the dismissal
reason and comment for every alert we dismiss, and the PR bodies hold every other decision
(bumps, overrides, floors, mitigations, accepted risks, verification). Never edit the
`overrides` block of a `package.json` or add a floor to `pyproject.toml` without explaining
why in the PR.

## Manifests

Three dependency trees, each with its own lockfile and install command:

| Tree | Manifest | Lockfile | Install | Ships to |
|---|---|---|---|---|
| frontend | `package.json` | `package-lock.json` | `npm ci` | browser bundle (`npm run build`), Keycloak theme |
| e2e | `test/e2e/package.json` | `test/e2e/package-lock.json` | `npm ci` in `test/e2e` | CI and BrowserStack only |
| backend | `pyproject.toml` | `uv.lock` | `uv sync --frozen --extra cli --extra subscription` | Django app, celery worker, flower |

Everything in the e2e tree and every `devDependencies` entry in the frontend tree is dev or
test only. Frontend `dependencies` only reach users through the Vite bundle, so a package that
nothing under `assets/` imports is also unreachable in production.

## One pass, several PRs

Changes are split by gate so that the routine work merges every week and nothing waits on a
discussion it is not part of.

- **Routine PR**: branch `dependabot-<date>`. In-range re-resolutions, patch/minor parent
  upgrades, removal of dead or redundant overrides and floors, dismissals (with their reasons
  repeated in the body), accepted normal-risk groups. Merged by the person running the pass
  alone once CI is green. The body carries the pass summary: alerts before and after by
  severity, what was deferred for cooling and until when, links to the gated PRs.
- **One gated PR per decision**: `dependabot-<date>-bypass-<pkg>`, `dependabot-<date>-major-<pkg>`,
  `dependabot-<date>-<pkg>` for a high-risk choice. Each carries only its own rationale and
  asks for its own review. Gated: cooling-period bypasses; major bumps; high-risk no-clean-fix
  choices; any change to a package on the sensitive list below.

Gated PRs are branched from `main`, not stacked on the routine PR, and rebased after it merges.
A little duplicate lockfile churn between them is acceptable; a blocked routine PR is not.

**Sensitive packages** (auth, crypto, payments, storage). A change to any of these, or to a
transitive dependency reached only through one of them, is gated even when it is a patch bump:

- auth: `mozilla-django-oidc`, `pyjwt`, `djangorestframework-simplejwt`, `itsdangerous`,
  `django-cors-headers`
- crypto: `cryptography`, `argon2-cffi`
- payments: `paddle-python-sdk`, `@paddle/paddle-js`
- storage: `psycopg`, `redis`, `hiredis`, `celery`, `celery-redbeat`

Keep this list in step with `pyproject.toml` and the `dependencies` block of `package.json`.

## 0. Preconditions

- Clean checkout of `main`. Work starts on `dependabot-<date>` (date as `YYYY-MM-DD`); each
  gated change gets its own branch from `main` (step 6).
- Node and npm on PATH at the versions the dev container uses. A different npm major can
  reorder `package-lock.json`; if `npm ci` rewrites the lockfile, stop and match the version.
- `uv` on PATH, recent enough that `uv lock --help` lists `--exclude-newer`.
- `gh auth status` succeeds; the token can read and dismiss Dependabot alerts.
- Fresh installs so `node_modules` match the lockfiles: `npm ci` in the root and in `test/e2e`,
  `uv sync --frozen --extra cli --extra subscription`.
- Test environment: the Django suite uses SQLite and the committed `.env.test`, so it needs no
  containers. The flower smoke test needs a reachable redis (the dev stack exposes one on
  `localhost:6380`).

## 1. Collect the starting state

```sh
gh api "repos/thunderbird/thunderbird-accounts/dependabot/alerts?state=open&per_page=100" \
  --jq '.[] | "\(.number)\t\(.security_advisory.severity)\t\(.dependency.package.ecosystem)\t\(.dependency.package.name)\t\(.dependency.manifest_path)\t\(.security_vulnerability.vulnerable_version_range) -> \(.security_vulnerability.first_patched_version.identifier // "none")\t\(.security_advisory.ghsa_id)"'
npm audit --json > /tmp/audit-root-before.json
(cd test/e2e && npm audit --json > /tmp/audit-e2e-before.json)
```

Fetch each advisory (`gh api advisories/<ghsa>`) to see every vulnerable range and patched
version, not just the one Dependabot shows: a fix may exist in the parent's major.

Group alerts by the direct dependency that owns the path. For each group note: vulnerable
package and version, parent chain, each parent's declared range, fixed version, and whether the
path is **runtime** (shipped backend, celery, flower or frontend bundle) or **dev/test only**.
Also note whether any package in the group is on the sensitive list.

```sh
npm ls <pkg>                                         # parent chain (run in test/e2e for that tree)
npm view <parent>@<version> dependencies.<pkg>       # the parent's declared range
uv tree --invert --package <pkg>                     # Python parent chain
curl -s https://pypi.org/pypi/<parent>/<version>/json | jq '.info.requires_dist'
```

## 2. Classify risk first

Before choosing a fix, rate each group:

- **High risk**: runtime path, and the vulnerable code is reachable (the module is imported and
  the triggering input can come from a user or the network), or severity is critical/high on a
  runtime path and reachability cannot be ruled out.
- **Normal**: everything else (dev tooling, test-only, or runtime but provably unreachable).

A high-risk group is never deferred or accepted on your own judgement. When it has a clean fix
(rules 1-3 in step 3), apply it. When it doesn't (a young fix version, or only a breaking jump
or no fix at all), stop and put the decision to the person running the skill: lay out the
options, the risks and benefits of each (exposure while waiting, breaking changes and the code
they hit, test coverage of the vulnerable path, effort), and your recommendation. Apply only
the option they choose, in its own gated PR, with the decision recorded in that PR's
"Decision" section (see step 6).

## 3. Decide, one group at a time

**Cooling period first.** Neither npm nor uv has a persistent minimum-release-age setting, so
the 7-day cooling period is applied by hand on every re-resolution. Compute the cutoff once per
pass (`date -u -d '7 days ago' +%Y-%m-%dT00:00:00Z`) and check the fix version's age:

```sh
npm view <pkg>@<version> time.<version>
curl -s https://pypi.org/pypi/<pkg>/<version>/json | jq -r '.urls[0].upload_time_iso_8601'
```

If every patched version is younger than 7 days and the group is **normal** risk, defer the
group to the next pass: leave the alert open and list it under "Deferred for cooling period" in
the routine PR. If an older patched version exists, take the newest one that is at least 7 days
old. If the group is **high** risk and only young versions fix it, surface it for a human
decision (step 2): wait, or bypass. A bypass goes in its own gated PR
(`dependabot-<date>-bypass-<pkg>`), names the exact version and its publish date, and is
justified there.

Walk this list in order and stop at the first rule that applies. Then assign the result to a
PR: a major bump, a high-risk choice from rule 5, or anything touching a sensitive package goes
in its own gated PR; everything else goes in the routine PR.

1. **In range.** The fixed version satisfies every parent's declared range. Re-resolve it (see
   step 4) and remove any override or floor that becomes redundant. For a direct Python
   dependency, also raise its floor in `pyproject.toml` to the fixed version with a comment
   naming the advisory, following the existing CVE-pin entries there.
2. **Parent upgrade reaches the fix.** A newer release of the direct dependency pins or allows
   the fixed version. Bump the direct dependency's range in the owning manifest. Patch or minor
   freely; a major bump needs the changelog step and the coverage check, and goes in its own
   gated PR (`dependabot-<date>-major-<pkg>`). Remove overrides the bump makes redundant.
3. **Minimal override.** Only when the parent pins an exact version and the fix is a patch
   within the same major (for 0.x: the same minor). npm: one entry in the `overrides` block,
   using `"$<dep>"` when the package is also a direct dependency so the two never drift (the
   existing `"vue": "$vue"` is the model); pin exactly when a family of packages must move in
   lockstep (`@intlify/core-base` with `vue-i18n`). uv: a floor in `pyproject.toml` under the
   CVE-pin comment, which is the closest equivalent of an override.
4. **Dismiss as unreachable.** The fix would be a breaking jump and the vulnerable module or
   code path provably never loads: grep `assets/` and `src/` for imports of the trigger module,
   check which parent entry point requires it, check runtime config. Dismiss via the API with
   `dismissed_reason=not_used` and a comment of at most 280 characters. The comment is the
   permanent record for that alert, so it must stand on its own: what was checked, why the code
   never loads, and the condition that would make us revisit. Repeat the rationale in the
   routine PR's "Dismissed alerts" section:

   ```sh
   gh api -X PATCH repos/thunderbird/thunderbird-accounts/dependabot/alerts/<n> \
     -f state=dismissed -f dismissed_reason=not_used -f dismissed_comment="<rationale>"
   ```

5. **No clean fix.** Split by risk:
   - **High risk**: surface it for a human decision (step 2). The options to lay out: upgrade
     the parent across the major and adapt our code to its breaking changes; take the fixed
     sub-dependency via a forcing override and prove compatibility with tests that cover the
     parent's use of it; patch around the vulnerable behaviour in our own code (input
     validation, disabling the feature) while the upstream fix is pending; or accept/defer,
     leaving the alert open with a re-check condition. Whichever change they choose, add
     coverage for the vulnerable path.
   - **Normal risk, no fix upstream**: accept. List the package, why it is low risk, and the
     re-check condition in the routine PR's "Accepted / no upstream fix" section. If a
     Dependabot alert exists for it, leave the alert open; it is the reminder to re-check.

### Changelog step (every bump, including transitive ones)

Read the release notes between current and target version. Note breaking changes, Node or
Python engine changes, peer-dependency changes, and behaviour changes tests would not catch.

```sh
gh api "repos/<owner>/<repo>/releases?per_page=40" --jq '.[] | select(.tag_name | test("^v11[.]4[.]")) | "### \(.tag_name)\n\(.body)"'
npm view <pkg>@<version> dependencies peerDependencies engines
curl -s https://pypi.org/pypi/<pkg>/<version>/json | jq '.info.requires_dist, .info.requires_python'
```

### Test-coverage check (every runtime bump)

Map the package to its import sites and config in `assets/` and `src/`, then to the suites
that exercise them:

- frontend unit: `npm run test:frontend` (vitest)
- backend unit: `uv run python manage.py test thunderbird_accounts` (SQLite, no containers)
- e2e: `test/e2e` Playwright suite, run by `validate.yml` on PRs
- flower: no automated coverage; start it locally and probe `/healthcheck` (step 5)
- nightly BrowserStack suites do **not** run on PRs; treat them as uncovered.

If nothing exercises the path, add a test in the same PR that drives the vulnerable behaviour
through our code. Then proceed with the upgrade. The new test and what it proves go in the QA Log.

## 4. Apply and prune

Do steps 4 and 5 on the routine branch first, then on each gated branch (`git switch -c
dependabot-<date>-<...> main`), so every branch stands on its own against `main`. Pruning
belongs to the routine branch; a gated branch touches only what its decision needs.

Every lockfile change comes from an npm or uv command and is reviewed as its diff. Never edit a
lockfile by hand, and never run `npm audit fix` or `npm dedupe` (they rewrite unrelated
entries).

1. Edit `package.json` ranges and overrides or `pyproject.toml` floors as decided.
2. **npm, lifting a transitive within its parent's range** (run in the tree that owns it):

   ```sh
   npm update <pkg> --before=<cutoff>
   ```

   `--before` makes npm ignore releases published after the cutoff, which is how the cooling
   period is enforced. Then `git diff package-lock.json`: most changed lines should name
   `<pkg>`, and every other package that changed must be explained or the update reverted. If
   the version does not move, a parent pins it exactly: that is the parent-upgrade or override
   rule in step 3. After editing `overrides`, `npm install --before=<cutoff>` applies them.
3. **uv, lifting a package within its parents' ranges**:

   ```sh
   uv lock --upgrade-package <pkg> --exclude-newer <cutoff>
   uv lock
   ```

   The first command records `exclude-newer` in `uv.lock`'s `[options]`; the second drops it
   again while keeping the resolved versions (uv prefers the locked version when it still
   satisfies the ranges). `uv lock --check` must then pass. `git diff uv.lock` should name only
   `<pkg>` and the manifest floors you changed.
4. Check for new duplicate copies in the npm trees: compare the set of packages with more than
   one version against `main`. A second copy of a runtime library (`vue`, `vue-i18n`, `pinia`)
   is a regression; fix it with an override before moving on.
5. Prune overrides and floors: delete an npm override whose parents now resolve to a fixed
   version on their own (check with `npm view <parent> dependencies.<pkg>`), and a Python floor
   whose parents all require at least the fixed version. Keep every override that still holds
   a fixed version, and say so in the PR.
6. `npm ci` in both trees and `uv sync --frozen --extra cli --extra subscription` must succeed
   on the result without changing any lockfile.

## 5. Verify

Verify each branch separately; each PR's QA Log covers only its own branch.

- `npm audit --json` in both trees; compare with the before files. Remember `npm audit` keeps
  counting advisories we dismissed in GitHub.
- Frontend: `npm run test:frontend`, `npm run build`, `npm run build-theme`, `npx eslint assets/app/`.
- Backend: `uv lock --check`, `uv run python manage.py test thunderbird_accounts`,
  `uv run ruff check`, `uv run ruff format --check`.
- Flower when tornado, flower, celery or kombu moved: start
  `uv run celery --app thunderbird_accounts flower --port=5556 --broker=redis://localhost:6380/9`
  with `.env.test` exported and confirm `/healthcheck` returns 200.
- e2e when `test/e2e` changed: rely on the `run-e2e-tests-local` job in PR CI and say so in
  the QA Log; run `npm run e2e-test` locally against the dev stack if the change touches the
  Playwright or BrowserStack runtime itself.
- For every high-risk change chosen in step 3: run the new test against the *old* version too
  (it should fail or show the vulnerable behaviour) and against the new version (it passes).
  Both results go in the QA Log.
- `gh api ".../dependabot/alerts?state=dismissed"` shows the new dismissals with their comments.
- `git diff main -- package.json test/e2e/package.json pyproject.toml` shows only removals plus
  the justified additions.

## 6. Commit and open the PRs

**Commits are concise** and follow `AGENTS.md`: a single capitalised sentence, then a
"Before... Now..." body of a few lines naming the direct bumps, override and floor changes,
and alert numbers fixed. Commit the dependency changes and their supporting tests separately
from any tooling or documentation changes. Do not put the verification narrative in the commit.

Open every PR against `main` so the Django suite and e2e run. Open the gated PRs first so the
routine PR can link to them. Link alerts by number so merging closes them.

**The PR is where the detail goes.** Routine PR body:

```markdown
## Summary
Pass summary: open alerts before -> after by severity (critical/high/medium/low), direct
bumps, overrides and floors before -> after.

## Gated PRs
Link and one line per gated PR opened in this pass (omit if none).

## Changes by alert
| Alert | Package | Parent declares | Fix | Decision |
one row per group in this PR, decisions in the words of step 3

## Overrides
Added (with justification) / removed (with why they became redundant).

## Dismissed alerts
Alert numbers, package, one-line rationale each (the 280-char API comment points here).

## Accepted / no upstream fix
Package, why it is low risk, re-check condition.

## Deferred for cooling period
Package, fix version, publish date, eligible date.

## QA Log
- bulleted list of every verification step actually run, with the command and the result
  (counts of test files/tests, build status, frozen-install result, audit before/after)
- what was NOT run locally and is left to PR CI (e2e)
- lockfile duplicate check result
```

Gated PR body, one per decision:

```markdown
## Decision
What needs review and why it is gated (bypass, major, high-risk choice, sensitive package).
For a high-risk group: what was reachable and how, the options presented with their risks and
benefits, who decided, what they chose and why, and the re-check condition if accepted or
deferred. For a major: breaking changes handled and where our code changed. For a bypass: the
exact version and publish date, why it could not wait.

## Changes by alert
| Alert | Package | Parent declares | Fix | Decision |

## QA Log
Same as the routine PR, plus for each new test: file, what it drives, result against the old
and new versions.
```

**After the routine PR merges**, rebase each open gated branch onto `main`. Do not hand-merge
conflicts in a lockfile: take `main`'s copy, re-apply the branch's manifest edits, and re-run
the commands from step 4 (`npm update <pkg> --before=...` or `uv lock --upgrade-package
<pkg> --exclude-newer ...` followed by `uv lock`), using the PR's "Changes by alert" table as
the list. Then re-run the audits and confirm every alert the PR claims to fix is still fixed
before running the frozen installs. Force-push with `--force-with-lease`.
