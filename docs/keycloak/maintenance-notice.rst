====================
Maintenance notice
====================

The Keycloak login page (``auth.tb.pro``) can show a maintenance or incident notice, with an optional link to a status
page, above the invite-only notice. Accounts pages (``accounts.tb.pro``) with the standard header, including the
dashboard, show the same notice under the header, so signed-in users see it too. The text is a Keycloak message that
you set as a **realm
localization override** on the ``tbpro`` realm, so it appears without a deploy or restart. See
`#1490 <https://github.com/thunderbird/thunderbird-accounts/issues/1490>`_.

How it works
------------

* The ``tbpro`` login theme defines these messages in ``keycloak/themes/tbpro/login/messages/messages_en.properties``:

  * ``maintenanceNotice``: the notice text. Empty by default, which shows no notice.
  * ``maintenanceNoticeType``: ``info``, ``warning`` (default) or ``critical``. Sets the bar's colour and icon. Any
    other value is treated as ``warning``.
  * ``maintenanceNoticeStatusUrl``: optional status page URL, linked after the notice text. Only ``http`` and
    ``https`` URLs are linked; anything else is ignored.
  * ``maintenanceNoticeStatusText``: the link text, ``Status`` by default.

* When ``maintenanceNotice`` is not blank, the login screen shows it in its own bar above the other notices, so it
  stays visible next to a sign-in error. The text is shown exactly as typed, including quotes and braces; HTML is
  shown literally.
* A realm override replaces a theme message for that realm. Keycloak stores it in its database, shares it across
  nodes, and keeps it across restarts.
* Accounts reads the English overrides with its Keycloak admin client
  (``GET /admin/realms/tbpro/localization/en``) and applies the same rules to the type and status URL. It caches the
  result for ``MAINTENANCE_NOTICE_CACHE_SECONDS`` (default 60), so a change can take that long to show on Accounts
  pages. If Keycloak does not answer within ``MAINTENANCE_NOTICE_TIMEOUT_SECONDS`` (default 2) or returns an error,
  Accounts shows no notice, logs a warning and caches that result for the same time.

Turning the notice on or off
----------------------------

#. In the Keycloak admin console, switch to the ``tbpro`` realm. The console opens in the **master** realm, so click
   **Manage realms** in the left sidebar and click ``tbpro`` (display name *Thunderbird Accounts*). Overrides saved in
   any other realm have no effect on the login page.
#. Open **Realm settings → Localization → Realm overrides** and select the language.
#. Enter each key and value separately with **Add translation**, then click **Create**. For example:

   * Key ``maintenanceNotice``, value ``Thundermail is currently unavailable. We are working to restore service.``
   * Key ``maintenanceNoticeType``, value ``critical``
   * Key ``maintenanceNoticeStatusUrl``, value the status page URL, for example ``https://status.example.org/``

#. Open the login page in a private window and check the notice and its link. Within a minute it also shows on
   Accounts pages.
#. To remove the notice, delete the rows you added with **⋮ → Delete**. Overrides survive Keycloak restarts, so the
   notice stays until it is deleted. Accounts pages stop showing it within a minute.

The same overrides can be set through the admin REST API with an access token for a master-realm client that can
manage the ``tbpro`` realm:

.. code-block:: shell

    CLIENT_ID=...      # master-realm client allowed to manage tbpro
    CLIENT_SECRET=...
    TOKEN=$(curl -s -d grant_type=client_credentials -d "client_id=$CLIENT_ID" -d "client_secret=$CLIENT_SECRET" \
      https://auth.tb.pro/realms/master/protocol/openid-connect/token | jq -r .access_token)

    curl -X PUT -H "Authorization: Bearer $TOKEN" -H 'Content-Type: text/plain' \
      --data 'Thundermail is currently unavailable. We are working to restore service.' \
      https://auth.tb.pro/admin/realms/tbpro/localization/en/maintenanceNotice

    curl -X PUT -H "Authorization: Bearer $TOKEN" -H 'Content-Type: text/plain' \
      --data 'critical' \
      https://auth.tb.pro/admin/realms/tbpro/localization/en/maintenanceNoticeType

    curl -X PUT -H "Authorization: Bearer $TOKEN" -H 'Content-Type: text/plain' \
      --data 'https://status.example.org/' \
      https://auth.tb.pro/admin/realms/tbpro/localization/en/maintenanceNoticeStatusUrl

    for key in maintenanceNotice maintenanceNoticeType maintenanceNoticeStatusUrl; do
      curl -X DELETE -H "Authorization: Bearer $TOKEN" \
        "https://auth.tb.pro/admin/realms/tbpro/localization/en/$key"
    done

Locally
-------

The local admin console is at http://keycloak:8999/admin/master/console/ (``admin`` / ``admin``). The steps are the
same.

Limitations
-----------

* The notice is stored in Keycloak, so it cannot announce a Keycloak outage: during one, neither the login page nor
  Accounts can show it. That needs a notice outside Keycloak.
* Of the Keycloak pages, only the login screen shows the notice. Registration, password reset and other Keycloak pages
  do not. Accounts pages without the standard header (sign-up, and the error and not-found pages) do not either.
* Overrides are per locale. The realm offers English and German, and German falls back to the English override
  because the theme has no German messages. If the theme gains ``messages_de.properties`` with a
  ``maintenanceNotice`` line, German visitors see that instead, so set a German override too. Accounts always shows
  the English override.
* There is no scheduled start or end time; turn the notice on and off by hand.
