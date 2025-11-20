Mail App
--------

The Mail App is a module of code located in ``/src/thunderbird_accounts/mail/`` which deals with our integration with to a Stalwart mail server and directory server / user management. To allow ORM usage and keep track of Stalwart principal objects we create :any:`thunderbird_accounts.mail.models.Account` and :any:`thunderbird_accounts.mail.models.Email` models that are essentially just pointers.
Additionally this module contains logic for retrieving and updating Stalwart, and hosts the home view which is used in the frontend.

Admin Panel
-----------

This is the standard Django admin panel with minor tweaks to help suit our needs.

Stalwart's user management is actively controlled by :any:`thunderbird_accounts.mail.models.Account` model in this app. This Account object is created in :any:`thunderbird_accounts.subscription.utils.activate_subscription_features()` during the Paddle ``subscription.created`` webhook and is manually called during local development after the Paddle sandbox checkout.

Dashboard
-----------

The self-serve portal is available at ``/dashboard``. This route requires the user to be authenticated.

Here a user can view the settings required to connect to their mail account, and create / delete app passwords to access their mail.

From a development perspective most of the development happens in the VueJS app located in ``assets/app/app.ts``.
