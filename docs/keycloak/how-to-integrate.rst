==============================================
How to integrate Keycloak
==============================================

This documentation is written for the Thunderbird Pro team.

To connect your service to Thunderbird Pro Accounts (Keycloak) you'll want to use a standard oidc client library.

Below is a few libraries already in use:

* JavaScript/TypeScript: `oidc-client-ts <https://github.com/authts/oidc-client-ts>`_
* Python/Django: `mozilla-django-oidc <https://github.com/mozilla/mozilla-django-oidc>`_
* Python: `Authlib <https://pypi.org/project/Authlib/>`_

Generally any oidc library will do. To allow for ease of self-hosting in the future you should however be using a generic oidc library and not one specific to Keycloak.

Client side
-----------

For client-side services (i.e. services that run entirely on the client) you'll be given a client id and asked to perform the authentication with PKCE enabled.

Here you'll use your library to ensure the token is valid, and to refresh the token in circumstances where that's okay to do. An example for the oidc-client-ts library can be found `here <https://github.com/authts/oidc-client-ts/blob/main/docs/protocols/authorization-code-grant-with-pkce.md>`_.

If your service has an API (see the next section) you'll want to authenticate it against the token by passing the JWT to the server in some authentication header.

Server side
-----------

For server-side services you'll be given both a client id and a client secret, and the client will be given confidential access. We do not currently store any secure or confidential data on Keycloak so it's functionally identical to a non-confidential/client side client.

For verifying or authenticating that a token is still valid you can use your library or just make a request to Keycloak's token introspection route like so:

.. code-block:: python

    from authlib.integrations.requests_client import OAuth2Session
    from requests import Response

    def get_expiry_time_with_grace_period(expiry: int):
        """Retrieve the grace period where an invalid token is still valid"""
        grace_period = max(int(os.getenv('OIDC_EXP_GRACE_PERIOD', 0)), 120)
        expiry += grace_period
        return expiry

    def verify_token(access_token: str):
        # Retrieve the OAuth2Session object so we can make requests
        client = OAuth2Session(
            client_id=os.getenv('OIDC_CLIENT_ID'), client_secret=os.getenv('OIDC_CLIENT_SECRET')
        )

        # Make a request against the introspect token route to verify the token is still okay
        response: Response = self.client.introspect_token(
            os.getenv('OIDC_TOKEN_INTROSPECTION_URL'), token=access_token, token_type_hint='access_token'
        )

        response.raise_for_status()
        data = response.json()

        # Handle expiry (if the token is expired fail the request)
        expiry = data.get('exp')
        if expiry:
            # Grace period maxes out at 2 minutes (120 seconds)
            expiry = get_expiry_time_with_grace_period(expiry)
            if expiry < datetime.datetime.now(datetime.UTC).timestamp():
                return None

        # Ensure the token is still active
        if data.get('active') is not True:
            return None

        return data

You could additionally refresh the token server-side and propagate that change down to the client, but for appointment we just let the client handle it.

Verifying subscription status
-----------------------------

During the server side (via the introspect token call) or via the JWT itself you should receive data similar to this shape:

.. code-block:: javascript

    {
      "exp": 1763596388,
      "iat": 1763596088,
      "jti": "ofrtna:d791b454-5700-73b4-8619-1d46a27b24f2",
      "iss": "http://keycloak:8999/realms/tbpro",
      "aud": "account",
      "sub": "5f75218f-1cb0-49a5-bd1c-e38c3b32dbd2",
      "typ": "Bearer",
      "azp": "tb-accounts",
      "sid": "db22f187-3a97-4621-a7ac-ef5039d46358",
      "acr": "1",
      "allowed-origins": [
        "http://localhost:8087/*"
      ],
      "realm_access": {
        "roles": [
          "offline_access",
          "uma_authorization",
          "default-roles-stalwart"
        ]
      },
      "resource_access": {
        "account": {
          "roles": [
            "manage-account",
            "manage-account-links",
            "view-profile"
          ]
        }
      },
      "scope": "openid profile offline_access email",
      "zoneinfo": "America/Vancouver",
      "email_verified": true,
      "mail_storage_bytes": "100073741824",
      "mail_address_count": 100,
      "mail_domain_count": 100,
      "preferred_username": "admin@example.org",
      "given_name": "Admin",
      "locale": "en",
      "name": "Admin Example",
      "is_subscribed": false,
      "session_state": "db22f187-3a97-4621-a7ac-ef5039d46358",
      "send_storage_bytes": "100073741824",
      "family_name": "Example",
      "email": "admin@example.com"
    }

You should additionally gate your authentication by checking if ``is_subscribed === true``.

If any other value than true you should immediately abort any requests and send the user to the following urls based on your environment:

* Dev/Stage: `<https://accounts-stage.tb.pro/subscribe>`_
* Production: `<https://accounts.tb.pro/subscribe>`_

From there the user will be presented with the subscription screen, and once subscribed the attribute ``is_subscribed`` will be flipped to true. The user won't automatically be sent back to the service they logged into but they will instead be sent to a dashboard with links to each service.

Reading plan information
------------------------

Your service may restrict various aspects or features based on a user's plan. The plan information isn't presented to you, but instead their plan details are obtainable by reading the token introspect return data, or by decoding the JWT on the client-side.

The following plan information is available to use:

* ``mail_address_count``: The amount of email aliases a user can create.
* ``mail_domain_count``: The amount of custom domains a user can connect to their account for use with aliases.
* ``mail_storage_bytes``: The max amount of email storage they have access to. This value is stored in bytes.
* ``send_storage_bytes``: The max amount of Send storage they have access to. This value is stored in bytes.

It is your service's responsibility to use and check these limits as needed.

The reason why their plan isn't listed is to reduce the need to look up static plan information. Additionally a user could potentially be granted more aliases, or storage than their plan normally provides. You should always check the incoming plan details and update the values as needed.

Subscription Deactivation
-------------------------

Currently we aren't handling subscription deactivations. This will change in the future and require your service to build out a webhook to receive user events as they happen.



