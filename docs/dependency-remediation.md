# Dependency vulnerability remediation

Our policy for fixing Dependabot findings across the three dependency trees: the frontend
(`package.json`), the e2e harness (`test/e2e/package.json`) and the backend (`pyproject.toml`).
The procedure that implements it is `.claude/skills/dependency-remediation/SKILL.md`. It was
adopted from the tbpro-add-on repository (thunderbird/tbpro-add-on#1306) and adapted to npm and
uv.

By using a more deliberate process than `npm audit fix`, we reduce risk and avoid unnecessary
churn. This means:

- We avoid changing dependencies when the vulnerable code is not reachable by us.
- We keep `overrides` and version floors to a minimum, because each one forces a re-resolution
  that can introduce *new* vulnerabilities while we fix others.
- We check that the sub-dependency is compatible with its parent.
- We consider upgrading the parent of a vulnerable sub-dependency instead of overriding.
- We detect missing test coverage related to dependency upgrades and add it.

## Decision order

For each advisory group, take the first rule that applies:

1. **In range.** The fixed version already satisfies every parent's declared range. Re-resolve
   it (`npm update <pkg>` in the owning tree, `uv lock --upgrade-package <pkg>`), applying the
   cooling period below. For a direct Python dependency, also raise its floor in
   `pyproject.toml` with a comment naming the advisory.
2. **Parent upgrade.** A newer direct dependency pins or allows the fix. Bump it (patch/minor
   freely; major only after the changelog and coverage checks below).
3. **Minimal override.** The parent pins an exact version and the fix is a patch within the same
   major. One narrow npm `overrides` entry, or one `pyproject.toml` floor.
4. **Dismiss as unreachable.** The fix would be a breaking jump and the vulnerable code provably
   never loads in this app. Dismiss the Dependabot alert with reason `not_used` and a comment
   that records why and when to revisit.
5. **No clean fix.** No fix exists, or the only fix is a breaking jump.
   - **High risk** (runtime path, vulnerable code reachable or not ruled out): a human decides.
     The skill lays out the options (upgrade across the major and adapt our code, forcing
     override, mitigation in our own code, or accept/defer) with the risks and benefits of each
     and a recommendation, and applies only the option chosen. The decision and who made it go
     in the PR.
   - **Normal risk**: accept or defer, with a re-check condition. The Dependabot alert stays open.

Every bump gets its release notes read. Every runtime bump gets a **test-coverage check**.
If the case is not covered, add coverage and proceed.

## Cooling period

Neither npm nor uv offers a persistent minimum-release-age setting, so the cooling period is
applied at resolution time: `npm update <pkg> --before=<cutoff>` and
`uv lock --upgrade-package <pkg> --exclude-newer <cutoff>`, with the cutoff set to 7 days before
the pass. Malicious releases are typically pulled from the registry within hours to a few days,
so a week keeps nearly all of them out of the lockfiles at the cost of fixes landing a week late.

Two rules follow:

- A fix version younger than 7 days is **deferred to the next pass** unless the group is
  high risk, or an older release also carries the fix. The Dependabot alert stays open as the
  reminder.
- For a high-risk group, a human decides whether to wait or bypass the cooldown. A bypass names
  the exact version and its publish date in its own gated PR.

## Primary metric

**Open Dependabot alerts**, not `npm audit`, is our primary metric. `npm audit` keeps counting
advisories we dismissed in GitHub, and the e2e tree carries advisories inside
`browserstack-node-sdk` that Dependabot does not surface.
