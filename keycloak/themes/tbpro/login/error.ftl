<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        // <#if skipLink??>
        actionUrl: null,
        actionText: '',
        // <#else>
          // <#if client?? && client.baseUrl?has_content>
          actionUrl: '${client.baseUrl}',
          actionText: '${kcSanitize(msg("backToApplication"))?no_esc}',
          // </#if>
        // </#if>
      };
      window._l10n = {
        ...window._l10n,
        errorTitle: '${kcSanitize(msg("errorTitle"))?no_esc}',
      };
    </script>
    <#elseif section = "ignore-header">
        ${kcSanitize(msg("errorTitle"))?no_esc}
    <#elseif section = "ignore-form">
        <div id="kc-error-message">
            <p class="instruction">${kcSanitize(message.summary)?no_esc}</p>
            <#if skipLink??>
            <#else>
                <#if client?? && client.baseUrl?has_content>
                    <p><a id="backToApplication" href="${client.baseUrl}">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
                </#if>
            </#if>
        </div>
    </#if>
</@layout.registrationLayout>