==============================================
Client Webhooks
==============================================

Currently we only require and use an Auth type :any:`thunderbird_accounts.client.models.ClientWebhook`.

Request headers
===============

A webhook is always sent with the following headers

.. code-block:: json

  {
    "X-TBA-Timestamp": "<unix timestamp in UTC when sending the event was attempted>",
    "X-TBA-Signature": "<sha256 hash used for verification>"
  }

Depending on the event, a webhook can be sent with additional headers. Please see the events section for more information on specific events.

Verifying a webhook
===================

Compute a sha256 hash with hmac derived from the contents of the payload (request body as json) with your webhook's secret as they key.

Using a secure string comparison (e.g. https://docs.python.org/3/library/secrets.html#secrets.compare_digest or https://nodejs.org/dist/latest/docs/api/crypto.html#cryptotimingsafeequala-b) ensure the contents of ``X-TBA-Signature`` and your computed hash are equal.

If they are not equal, disregard any payload data and discard the webhook request.

You can examine  :any:`thunderbird_accounts.client.utils.create_webhook_hash` on how the ``X-TBA-Signature`` header is computed.

Events
======

* ``delete-user`` : This event notifies a client that they **must** remove a user and all of their associated user data.

Payload:

.. code-block:: json

  {
    "user_uuid": "<The user's uuid>"
  }


Headers:

.. code-block:: json

  {
    "X-TBA-Event": "delete-user"
  }