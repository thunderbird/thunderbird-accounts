Mail App
--------

The Mail App is a module of code located in `/src/thunderbird_accounts/mail/` which deals with our integration with to a Stalwart mail server and directory server / user management. We host part of their external directory server sql schema within Django with some minor tweaks to make things play nice. Currently we only have admin panel access, and basic user management via a self-serve page.

===========
Admin Panel
===========

This is the standard Django admin panel with minor tweaks to help suit our needs.

Stalwart's user management is actively controlled by `Account` model in this app. Currently, this is the recommended way to create a user account as we don't have sign-up enabled just yet.
