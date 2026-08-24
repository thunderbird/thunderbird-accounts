==============
Feature Flags
==============

We use django-waffle for feature flags and switches. Define each control in the
admin UI (or through a data migration) before referencing it in code, and use a
constant for its name to avoid mistakes. Add new controls to this page so it
remains the canonical inventory.

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Name
     - Type
     - Description
   * - ``auth-allow-post-reauth``
     - Flag
     - Allows the authentication middleware to try refreshing an inactive
       access token during non-GET requests when the refresh token is active.
   * - ``auth-introspect-token-per-request``
     - Flag
     - Makes the authentication middleware introspect the OIDC access token on
       every request.
   * - ``custom-domains-revamp``
     - Flag
     - Moves custom-domain management from the Mail dashboard to the dedicated
       Custom Domains page and displays navigation to that page.
   * - ``multi-factor-authentication``
     - Flag
     - Displays the Multi-factor Authentication links and pages on the
       dashboard.
   * - ``purge-incomplete-signups``
     - Switch
     - Makes ``purge_incomplete_signups`` delete stale users. When inactive,
       the task moves them into the "Users to Purge" group instead.
   * - ``show-connect-now``
     - Flag
     - Displays the Connect Now button in the Mail dashboard, which launches
       Thunderbird Desktop through a custom protocol URL.
