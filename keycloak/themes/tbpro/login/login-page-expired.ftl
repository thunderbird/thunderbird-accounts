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
    <#elseif section = "ignore-header">
        ${msg("pageExpiredTitle")}
    <#elseif section = "ignore-form">
        <p id="instruction1" class="instruction">
            ${msg("pageExpiredMsg1")} <a id="loginRestartLink" href="${url.loginRestartFlowUrl}">${msg("doClickHere")}</a> .<br/>
            ${msg("pageExpiredMsg2")} <a id="loginContinueLink" href="${url.loginAction}">${msg("doClickHere")}</a> .
        </p>
    </#if>
</@layout.registrationLayout>
