==============
Feature Flags
==============

We now use django-waffle for feature flags. You must define your feature flag in the admin ui (or via a data migration) then you can reference it throughout your code. 

Please use constants to avoid mistakes.

+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| Flag Name                        | Type   | Description                                                                                                                                       |
+==================================+========+===================================================================================================================================================+
| custom-domains-revamp            | flag   | Enables the new Custom Domains UI in the new /custom-domains route.                                                                               |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| multi-factor-authentication      | flag   | Displays the Multi-factor Authentication link and pages on the dashboard.                                                                         |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| active-logins                    | flag   | Displays the Security Settings card on /settings/security.                                                                                        |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| show-connect-now                 | flag   | Displays the 'Connect now' button in the Mail dashboard that triggers Thunderbird Desktop                                                         |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| send-storage                     | flag   | Displays the Send storage usage bar on the dashboard and enables the /api/v1/subscription/send/storage/ endpoint.                                 |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| app-password-management          | flag   | Shows the named multi app password manager on the dashboard and enables the /api/v1/mail/app-passwords/ list, create and revoke endpoints.       |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| purge-incomplete-signups         | switch | When active, purge_incomplete_signups will delete stale users. When inactive (default) it will move stale users into the "Users to Purge" group.  |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| increased-traffic-banner         | switch | When active, displays a sitewide banner telling users the site is under heavy load. Hidden by default.                                            |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+
| is-address-taken-lookup-stalwart | switch | During the is_address_taken function lastly check Stalwart for the address that is being requested, and error if that address exists in Stalwart. |
+----------------------------------+--------+---------------------------------------------------------------------------------------------------------------------------------------------------+

The ``app-password-management`` flag requires ``STALWART_ADMIN_API_USE_JMAP=True``.
When the flag is inactive or the legacy Stalwart admin API is in use, the existing
app password form remains active and the management endpoints return 404.
