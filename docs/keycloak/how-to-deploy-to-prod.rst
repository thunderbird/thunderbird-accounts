=================================
Updating and deploying Keycloak
=================================

A Keycloak image change on ``main`` publishes to GHCR and creates a numbered
GitHub draft release. Kargo promotes the Accounts and Keycloak image pair to
``tb-dev`` and ``tb-stage``. Publishing the draft requests promotion to
``tb-prod``.

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

Confirm that ``publish-images`` succeeded for the intended commit. In Kargo,
find the Freight with the expected Accounts and Keycloak image digests and
confirm it is verified in ``tb-stage``. Run the stage BrowserStack workflow
after that rollout. Check login, MFA, introspection, mail authentication, and
Keycloak configuration reconciliation.

3. Promote and verify production
--------------------------------

Publish the GitHub draft for that commit. Confirm that the
``promote-release-to-tb-prod`` workflow succeeds and Kargo shows the expected
Freight as current in ``tb-prod``.

Check `Keycloak discovery
<https://auth.tb.pro/realms/tbpro/.well-known/openid-configuration>`__ and
`Accounts health <https://accounts.tb.pro/health>`__. Check the Keycloak
rollout and configuration reconciliation logs in Argo CD. Use the dedicated
test account to sign in, complete MFA, confirm the custom theme and configured
MFA methods, then send and read a test message.

Rollback
--------

Ask the Kargo operator to select the previous verified Freight. Check Keycloak's
migration guidance before reverting an image across a database migration. Use
the approved database-restore procedure if the migration requires it.
