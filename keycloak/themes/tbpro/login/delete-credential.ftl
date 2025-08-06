<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        deleteCredentialTitle: '${msg("deleteCredentialTitle", credentialLabel)}',
        deleteCredentialMessage: '${msg("deleteCredentialMessage", credentialLabel)}',

      };
      window._l10n = {
        ...window._l10n,
        doConfirmDelete: '${msg("doConfirmDelete")}',
        doCancel: '${msg("doCancel")}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
