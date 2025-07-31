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
        requiredActions: [
            //<#if requiredActions??><#list requiredActions>
              //<#items as reqActionItem>
              '${kcSanitize(msg("requiredAction.${reqActionItem}"))?no_esc}',
              //</#items>
            // </#list></#if>
        ],
      };
    </script>
    <#elseif section = "ignore-header">
        <#if messageHeader??>
            ${kcSanitize(msg("${messageHeader}"))?no_esc}
        <#else>
        ${message.summary}
        </#if>
    <#elseif section = "ignore-form">
    <div id="kc-info-message">
        <p class="instruction">${message.summary}<#if requiredActions??><#list requiredActions>: <b><#items as reqActionItem>${kcSanitize(msg("requiredAction.${reqActionItem}"))?no_esc}<#sep>, </#items></b></#list><#else></#if></p>
        <#if skipLink??>
        <#else>
            <#if pageRedirectUri?has_content>
                <p><a href="${pageRedirectUri}">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
            <#elseif actionUri?has_content>
                <p><a href="${actionUri}">${kcSanitize(msg("proceedWithAction"))?no_esc}</a></p>
            <#elseif (client.baseUrl)?has_content>
                <p><a href="${client.baseUrl}">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
            </#if>
        </#if>
    </div>
    </#if>
</@layout.registrationLayout>