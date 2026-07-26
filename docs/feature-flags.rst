==============
Feature Flags
==============

We now use django-waffle for feature flags. You must define your feature flag in the admin ui (or via a data migration) then you can reference it throughout your code. 

Please use constants to avoid mistakes.

+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| Flag Name                   | Type   | Description                                                                                                                                      |
+=============================+========+==================================================================================================================================================+
| multi-factor-authentication | flag   | Displays the Multi-factor Authentication link and pages on the dashboard.                                                                        |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
| purge-incomplete-signups    | switch | When active, purge_incomplete_signups will delete stale users. When inactive (default) it will move stale users into the "Users to Purge" group. |
+-----------------------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------+
