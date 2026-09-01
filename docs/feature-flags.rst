==============
Feature Flags
==============

We now use django-waffle for feature flags. You must define your feature flag in the admin ui (or via a data migration) then you can reference it throughout your code. 

Please use constants to avoid mistakes.

+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| Flag Name                   | Type   | Description                                                                                                                                      |
+=============================+========+==================================================================================================================================================+
| custom-domains-revamp       | flag   | Enables the new Custom Domains UI in the new /custom-domains route.                                                                                  |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| multi-factor-authentication | flag   | Displays the Multi-factor Authentication link and pages on the dashboard.                                                                        |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| show-connect-now            | flag   | Displays the 'Connect now' button in the Mail dashboard that triggers Thunderbird Desktop                                                        |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| purge-incomplete-signups    | switch | When active, purge_incomplete_signups will delete stale users. When inactive (default) it will move stale users into the "Users to Purge" group. |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| increased-traffic-banner    | switch | When active, displays a sitewide banner telling users the site is under heavy load. Hidden by default.                                           |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
