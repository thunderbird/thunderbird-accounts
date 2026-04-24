<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
  <#if section = "js">
    <script>
      window._page['currentView'] = {
        // <#if skipLink??>
        actionUrl: null,
        actionText: '',
        // <#else>
          // <#if pageRedirectUri?has_content>
          actionUrl: '${pageRedirectUri}',
          actionText: '${kcSanitize(msg("backToApplication"))?no_esc}',
          // <#elseif actionUri?has_content>
          actionUrl: '${actionUri}',
          actionText: '${kcSanitize(msg("proceedWithAction"))?no_esc}',
          // <#elseif (client.baseUrl)?has_content>
          actionUrl: '${client.baseUrl}',
          actionText: '${kcSanitize(msg("backToApplication"))?no_esc}',
          // </#if>
        // </#if>
        // <#if messageHeader??>
        messageHeader: '${kcSanitize(msg("${messageHeader}"))?no_esc}',
        // <#else>
        messageHeader: null,
        // </#if>
        requiredActions: {
            //<#if requiredActions??><#list requiredActions>
              //<#items as reqActionItem>
              ${reqActionItem}: '${kcSanitize(msg("requiredAction.${reqActionItem}"))?no_esc}',
              //</#items>
            // </#list></#if>
        },
      };
      window._l10n = {
        ...window._l10n,
        infoRedirectTitle: '${kcSanitize(msg("infoRedirectTitle"))?no_esc}',
        infoRedirectText: '${kcSanitize(msg("infoRedirectText"))?no_esc}',
        infoVerifyEmailTitle: '${kcSanitize(msg("infoVerifyEmailTitle"))?no_esc}',
        infoVerifyEmailText:'${kcSanitize(msg("infoVerifyEmailText"))?no_esc}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
