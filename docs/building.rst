==============================================
Building for Stage
==============================================

Right now to build for stage you must login to the ECR via:

.. code-block:: console

  $ aws ecr get-login-password --region eu-central-1 |
  docker login --username AWS \
      --password-stdin \
      768512802988.dkr.ecr.eu-central-1.amazonaws.com

After you're logged in you can build the image as a normal container.

.. note::

 If you're on an ARM machine (like a m-series macbook) you must specify the platform as --platform="linux/amd64".

.. code-block:: console

  $ docker build -f ./Dockerfile.stage --platform="linux/amd64" .

The output of which should contain a sha256 hash. You must now tag the build:

.. code-block:: console

  $ docker tag sha256:<hash> 768512802988.dkr.ecr.eu-central-1.amazonaws.com/thunderbird/accounts:<a unique tag>

Once you tag it you can finally push it up via the tag like so:

.. code-block:: console

  $ docker push 768512802988.dkr.ecr.eu-central-1.amazonaws.com/thunderbird/accounts:<a unique tag>

After that is all done, you should see in the AWS web ui.

If you want to deploy with this image you'll need to update the pulumi/config.stage.yaml's task_definition.container_definitions with your new tag. And follow that up with a pulumi up.


