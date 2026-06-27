<#import "template.ftl" as layout>
<@layout.registrationLayout; section>
  <#if section = "js">
  <script>
      window._page['currentView'] = {
        formAction: '${url.logoutConfirmAction?no_esc}',
        sessionCode: '${logoutConfirm.code}',
        clientUrl: '${client.baseUrl?no_esc}',
      };
      window._l10n = {
        ...window._l10n,
        logoutConfirmTitle: '${msg("logoutConfirmTitle")}',
        logoutConfirmHeader: '${msg("logoutConfirmHeader")}',
        doLogout: '${msg("doLogout")}',
        backToApplication: '${kcSanitize(msg("backToApplication"))?no_esc}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
