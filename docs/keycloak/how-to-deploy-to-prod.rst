=================================
Updating and deploying Keycloak
=================================

A Keycloak image change on ``main`` publishes to GHCR. After all selected
image jobs succeed, ``publish-images`` records both image digests in
``pair.yaml`` on ``kargo/accounts-pairs`` and a numbered GitHub draft release
is created. Kargo creates Freight from the record commit and promotes the
pair to ``tb-dev`` and ``tb-stage``. Publishing the draft requests promotion
to ``tb-prod``.

.. warning::

   Never put credential values, tokens, personal data, realm exports, or
   environment files in documentation, commits, PRs, screenshots, or shared
   logs.

1. Upgrade and test
-------------------

#. Read the `release notes <https://github.com/keycloak/keycloak/releases>`__
   and `migration guide
   <https://www.keycloak.org/docs/latest/upgrading/#migration-changes>`__ for
   every version crossed. Check database, OIDC, authentication-flow, theme,
   startup-option, and server-SPI changes.

#. Update both image stages in ``Dockerfile.keycloak``:

   .. code-block:: dockerfile

      FROM quay.io/keycloak/keycloak:<new-version> AS mfa-release
      ...
      FROM quay.io/keycloak/keycloak:<new-version> AS mfa-local

   Keep them equal and never use ``latest``. Do not update the informational
   ``keycloakVersion`` field in realm exports.

#. If an API used by ``keycloak-mfa-rest`` changed, release a compatible
   provider and update its version and checksum. Update config-cli only when
   required by its compatibility notes or tests.

#. Validate:

   .. code-block:: shell

      docker manifest inspect quay.io/keycloak/keycloak:<new-version>
      docker compose build keycloak
      docker compose up -d keycloak kcpostgres
      curl --fail http://localhost:9000/health/ready

#. Run the end-to-end suite from ``test/e2e/README.md``. Ensure the theme, OIDC,
   introspection, MFA/recovery, and mail-authentication tests did not skip.

#. Open and merge the upgrade PR with upstream links and test results.

2. Verify staging
-----------------

Confirm that the **Record image pair** job in ``publish-images`` succeeded for
the intended commit. On ``kargo/accounts-pairs``, find the newest ``pair.yaml``
whose top-level ``revision`` matches that commit. The record pins the Accounts
and Keycloak multi-architecture index digests and each image's source
revision. Find the Freight carrying that record commit and confirm it is
verified and current in ``tb-stage`` before running
``e2e-tests-browserstack-stage.yml`` manually from GitHub Actions. Confirm the
suite passed and use Kargo promotion history to confirm that Freight stayed
current throughout the run. Separately check login, MFA, introspection, mail
authentication, and Keycloak configuration reconciliation.
`Kargo Accounts project <https://kargo.pi.thunderbird.net/project/tb-accounts>`__

3. Promote and verify production
--------------------------------

Publish the GitHub draft for that commit. The ``promote-release-to-tb-prod``
workflow requires exactly one Freight carrying the newest matching record
commit, verified in ``tb-stage``. Confirm the workflow succeeds and Kargo
shows that Freight as current in ``tb-prod``. GitHub runs the workflow from the
tagged release commit, so releases pinned before the record lookup was
introduced still use the image-digest lookup.

Check `Keycloak discovery
<https://auth.tb.pro/realms/tbpro/.well-known/openid-configuration>`__ and
`Accounts health <https://accounts.tb.pro/health>`__. Check the Keycloak
rollout and configuration reconciliation logs in Argo CD. Use the dedicated
test account to sign in, complete MFA, confirm the custom theme and configured
MFA methods, then send and read a test message.

Seeding and recovery
--------------------

To seed the first record, run ``publish-images`` on ``main`` with
``seed_pair`` enabled. This skips the builds and records the digests and
source revisions of both current GHCR ``latest`` indexes. Check ``pair.yaml``
on ``kargo/accounts-pairs`` before switching the Kargo Warehouse. The seed
creates no draft release.

A failed or cancelled image job leaves the previous record in place. Check
for newer runs before retrying, since an older run can still move shared GHCR
tags. Resolve the failure and rerun ``publish-images`` for the same commit,
or publish the fix on ``main`` if it requires a source change. A rerun can
write another record for that commit. Check the Freight for the newest
matching record is verified in ``tb-stage`` before publishing the draft.
`CI image publishing and promotion <../ci/image-publish-pipeline.md>`__

Rollback
--------

Ask the Kargo operator to select the previous verified Freight. Check Keycloak's
migration guidance before reverting an image across a database migration. Use
the approved database-restore procedure if the migration requires it.
