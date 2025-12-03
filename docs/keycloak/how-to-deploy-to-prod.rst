==============================================
Deploying Keycloak theme changes to production
==============================================

Unlike our staging CI pipeline which does build and deploy Keycloak to https://auth-stage.tb.pro, our production CI pipeline does not.

To deploy any changes to production you must first grab the ``deployment-keycloak`` artifact from a staging build with the keycloak theme changes. 
Take the ``ecr_tag`` value from the ``deployment.json`` file and replace the container image in ``config.prod.yaml`` with it. 

After that switch your pulumi to production via ``pulumi stack select``, and run the following command to deploy to production:

.. code-block:: shell

	TBPULUMI_DISABLE_PROTECTION=True AWS_REGION=eu-central-1 pulumi up --diff --target 'urn:pulumi:prod::accounts::tb:**:*keycloak*' --target-dependents

When prompted, double check you're not breaking anything important and deploy the changes.
