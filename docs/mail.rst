Mail App
--------

The Mail App is a module of code located in `/src/thunderbird_accounts/mail/` which deals with our integration with to a Stalwart mail server and directory server / user management. We host part of their external directory server sql schema within Django with some minor tweaks to make things play nice. Currently we only have admin panel access, and basic user management via a self-serve page.

===========
Admin Panel
===========

This is the standard Django admin panel with minor tweaks to help suit our needs.

Stalwart's user management is actively controlled by `Account` model in this app. Creating an account model with a name and attaching it to a `Authentication.User` model allows a user to modify their account data in the self-serve page.

==========
Self Serve
==========

The self-serve portal is available at `/self-serve/`. This route requires the user to be authenticated.

Here a user can view the settings required to connect to their mail account, and create / delete app passwords to access their mail.

From a development perspective most of the development here happen in the template folder `/templates/mail/self-serve/` and the `mail/views.py` file. Currently development is quite primitive as we await designs, with a mixed VueJS / Django template pages.
