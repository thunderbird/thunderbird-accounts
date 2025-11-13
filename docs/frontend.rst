==============================================
Frontend Development
==============================================

To ensure that our look and feel is consistent with other Thunderbird Services we utilize VueJS and our Services-UI library.

Overview
--------

The Vue app is currently mounted in the ``templates/mail/index.html`` file through the  :any:`thunderbird_accounts.mail.views.home()` view function in the urls.py file.

There is a catch-all route that is used to mount the Vue app on all other routes that don't match the Django router.

Currently, we are already retrieving some important user information about subscription / plan / Stalwart account information before the Vue app is mounted and then injecting it through the ``window._page`` object.

However, this should be restricted to only the absolutely necessary user information. For data that could come later, please make a new endpoint and fetch it from the client-side.

Vue App Structure Guidelines
----------------------------

- Components that are shared between multiple different views, are generic enough and not yet included in the Services-UI library, should go on the ``assets/app/vue/components/`` folder.
- New pages should go on the ``assets/app/vue/views/`` folder. The idea is to create a folder for each page and then create a ``index.vue`` file in that folder so that all its related files that are specific to said page are co-located.

OIDC / Keycloak Theme Development
---------------------------------

Anything pertained to the OIDC / Keycloak theming (e.g. anything related with login pages, etc), is not done in ``assets/app/vue/`` so please refer to the keycloak-theme.rst file for more information.

Although it also uses Vue and Services-UI, this is a completely separate pipeline!
