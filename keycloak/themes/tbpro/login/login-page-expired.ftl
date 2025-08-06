<#import "template.ftl" as layout>
<@layout.registrationLayout; section>
<#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.registrationAction}',
        restartFlowUrl: '${url.loginRestartFlowUrl}',
        loginUrl: '${url.loginAction}',
      };
      window._l10n = {
        ...window._l10n,
        pageExpiredTitle: '${msg("pageExpiredTitle")}',
        pageExpiredMsg1: '${msg("pageExpiredMsg1")}',
        pageExpiredMsg2: '${msg("pageExpiredMsg2")}',
        doClickHere: '${msg("doClickHere")}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
