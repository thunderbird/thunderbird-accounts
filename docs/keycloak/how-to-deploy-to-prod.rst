=================================
Updating and deploying Keycloak
=================================

Merging a Keycloak change deploys staging automatically. Production is a
separate image-promotion PR followed by a manual Pulumi update. Do not create an
Accounts release or Keycloak release tag for this process.

.. warning::

   Never put credential values, tokens, personal data, realm exports, or
   environment files in documentation, commits, PRs, screenshots, or shared
   logs.

Access required
---------------

* GitHub CLI access to Actions artifacts, plus repository write access for the
  promotion PR.
* A local Docker engine.
* AWS credentials for the production deployment role, including ECR/ECS access
  and read access for load-balancer and log verification.
* Pulumi CLI authenticated to Pulumi Cloud with access to
  ``thunderbird/prod`` and its stack secrets.
* A staging-safe test login. Keycloak Admin API credentials are needed only for
  deeper live-flow checks.

Load credentials with the approved credential loader; never place their values
directly in commands or files.

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

The ``deploy-stage`` workflow builds an immutable ECR image, deploys it to
staging, and publishes ``deployment-keycloak/deployment.json``.

Before promotion, verify the workflow and post-deploy tests passed, staging is
running that exact image, ECS/load-balancer health is good, reconciliation logs
have no unexplained errors, and login, MFA, introspection, and mail
authentication work.

3. Promote the tested image
---------------------------

Download the artifact from the successful staging run:

.. code-block:: shell

   gh run download "$RUN_ID" \
     --repo thunderbird/thunderbird-accounts \
     --name deployment-keycloak \
     --dir "$ARTIFACT_DIR"
   jq -r .ecr_tag "$ARTIFACT_DIR/deployment.json"

Record the current ``.keycloak_image`` in ``pulumi/config.prod.yaml`` for
rollback. Create and merge a small PR changing only that anchor to the
artifact's exact ``ecr_tag``. Run production Pulumi from a clean checkout of
merged ``main``.

4. Deploy production manually
------------------------------

Prepare and authenticate the Pulumi environment:

.. code-block:: shell

   cd pulumi
   uv venv --python 3.12 --seed venv
   uv pip install --python venv/bin/python -r requirements.txt
   source venv/bin/activate
   export AWS_REGION=eu-central-1 AWS_DEFAULT_REGION=eu-central-1
   export IS_CI_AUTOMATION=yes
   pulumi login
   pulumi stack select thunderbird/prod
   aws sts get-caller-identity
   pulumi whoami
   pulumi stack --show-name

Verify those identities locally; do not paste their output into the PR.

Use only the exact Keycloak task-definition and service targets:

.. code-block:: shell

   TASKDEF_TARGET='urn:pulumi:prod::accounts::tb:fargate:FargateClusterWithLogging$aws:ecs/taskDefinition:TaskDefinition::accounts-prod-fargate-keycloak-taskdef'
   SERVICE_TARGET='urn:pulumi:prod::accounts::tb:fargate:FargateClusterWithLogging$aws:ecs/service:Service::accounts-prod-fargate-keycloak-service'

   TBPULUMI_DISABLE_PROTECTION=True pulumi preview \
     --stack thunderbird/prod --diff \
     --target "$TASKDEF_TARGET" --target "$SERVICE_TARGET"

Expect exactly one task-definition replacement and one service update.
Environment-array reordering can be diff noise; compare entries by name. Stop
for creates, deletes, or unrelated IAM, network, secret, load-balancer,
autoscaling, or application changes.

Do not use the broad ``**:*keycloak*`` target or an unrestricted update. After
approving the preview, apply the same two targets without ``--yes``:

.. code-block:: shell

   TBPULUMI_DISABLE_PROTECTION=True pulumi up \
     --stack thunderbird/prod --diff \
     --target "$TASKDEF_TARGET" --target "$SERVICE_TARGET"

5. Verify or roll back
----------------------

Wait for Pulumi and ECS steady state. Confirm all desired tasks and targets are
healthy, old targets drained, the running image matches staging, reconciliation
completed, and realm discovery, login, MFA, introspection, and mail
authentication work. A final targeted preview should report no changes.

For rollback, use the exact ECR image reference recorded before promotion, not
a Keycloak version tag or ``latest``, and repeat the production steps:

#. Create and merge a rollback PR that changes only ``.keycloak_image`` back to
   the previous reference.
#. Update a clean checkout to merged ``main``.
#. Rerun the Section 4 preview with the same two targets. Expect one task
   definition replacement and one service update back to the previous image.
#. Run the Section 4 ``pulumi up``, wait for ECS steady state, and repeat every
   verification above.
#. Run a final targeted preview and confirm that it reports no changes.

An image rollback does not reverse a database migration. Never deploy an older
Keycloak image across a migrated database unless Keycloak's migration guidance
explicitly supports it or the approved database-restore procedure is followed.
