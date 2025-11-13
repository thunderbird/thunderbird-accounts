===========
Mail App
===========

The Mail App is a module of code located in ``/src/thunderbird_accounts/mail/`` which deals with our integration with to a Stalwart mail server and directory server / user management. We host part of their external directory server sql schema within Django with some minor tweaks to make things play nice.

Admin Panel
-----------

This is the standard Django admin panel with minor tweaks to help suit our needs.

Stalwart's user management is actively controlled by  :any:`thunderbird_accounts.mail.models.Account` model in this app. This Account object is created in :any:`thunderbird_accounts.subscription.utils.activate_subscription_features()` during the Paddle ``subscription.created`` webhook and is manually called during local development after the Paddle sandbox checkout.
