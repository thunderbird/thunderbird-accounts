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
        // Only the Thundermail provisioning gate's deny reason is shown; other summaries stay hidden.
        // <#if message?has_content && (message.summary == msg("thundermailNotProvisioned"))>
        errorMessage: '${kcSanitize(message.summary)?js_string?no_esc}',
        // </#if>
      };
      window._l10n = {
        ...window._l10n,
        errorTitle: '${kcSanitize(msg("errorTitle"))?no_esc}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
