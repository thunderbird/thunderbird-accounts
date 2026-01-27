Sign Up & Allow Lists
---------------------

The sign up form is hosted within Keycloak and while the Keycloak realm's ``User registration`` setting is enabled the "Subscribe" link on the login form will only go to Keycloak. While the sign up form is served by Keycloak directly anyone can sign up and essentially create a login. They will still have to subscribe to our services, but there's no allow or block list in place. This required us to additionally serve the sign up form on Accounts if the ``User registration`` setting on Keycloak is disabled. This sign up form does a POST submit to Accounts directly, where we do additional checks like seeing if a recovery email matches one on the allow list. 

Within this document and discussion about Accounts you will see the terms ``Keycloak sign up form`` vs ``Accounts sign up form`` to distinguish between the two identical but different forms.

==============
AllowListEntry
==============

The :any:`thunderbird_accounts.authentication.models.AllowListEntry` model is the allow list. During the Accounts sign up form submission flow the ``Recovery Email`` field is checked against this allow list, and if the user is not on the allow list their sign up information is discarded and they are immediately forwarded to our wait list form hosted on `tb.pro <https://tb.pro/>`_.

If there is a match the user will instead be created on Keycloak and Accounts, and then forwarded to the Subscribe page. Their user will be in a ``unsubscribed`` state until we get a webhook from Paddle telling us they have an active subscription. (Note: The property is a property function that just checks to see if that Subscription object exists and is active as well as if the relationship to the user exists.)

