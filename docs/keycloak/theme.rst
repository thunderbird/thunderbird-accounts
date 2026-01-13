==============================================
Keycloak Theme Development
==============================================

Keycloak is the default OIDC provider for Thunderbird Account. While we use a staging instance under the tbpro-dev realm
for other projects, we spin up a keycloak docker container for theme development in this project.

You can find the contents of the keycloak theme 'tbpro' under

| thunderbird-accounts
| └── keycloak
|     └── themes
|         └── tbpro
|
|

Accessing template variables
----------------------------

Since Keycloak uses traditional server-side rendered templates any accessible template variables are normally loaded
into ``window._page`` for template level variables and ``window._page.currentView`` for any page specific variables.
Localization information can be retrieved from a flat ``window._l10n``.

Keycloak uses freemarker templates. If you need to hook up any of the template variables you can do so in
``template.ftl`` or the specific page's template. A good example of this is ``login.ftl`` where we append additional
variables to ``window._page.currentView``. Annoyingly these variables are expressed in a similar way to es6 template
literals. Be extra careful not to attempt to use them as such with the backtick character!

If you're missing a variable you can generally find it on the original template (under the base theme) or via the
template provider located `here <https://github.com/keycloak/keycloak/blob/main/services/src/main/java/org/keycloak/forms/login/freemarker/FreeMarkerLoginFormsProvider.java>`_.

Adjusting l10n
--------------

Localization can be modified via the ``messages_<locale>.properties`` file located under

| thunderbird-accounts
| └── keycloak
|     └── themes
|         └── tbpro
|             └── theme type (e.g. login, email, etc...)
|                 └── messages
|

If you add new localization you'll need to adjust the ``window._l10n`` variable in template.ftl

l10n pain points
----------------

Since we're essentially piping strings from one localization system to another there's some quirks you should be aware
of.

* Avoid using single quotes: ``''`` as it can cause rendering problems. Instead use this character: ``’``.
* Ensure you save the message properties file as UTF-8. Some editors don't do this.
* If you need to use a special character defined in `vue-i18n <https://vue-i18n.intlify.dev/guide/essentials/syntax#literal-interpolation>`_ you'll need to specify the linear interpolation via a ``.replaceAll``. (e.g. ``@thundermail.com".replace('@', "{'@'}")``.) Using curly braces will trip up keycloak's template rendering.
