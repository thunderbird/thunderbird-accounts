<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=true; section>
<#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        // <#if verifyEmail??>
        verifyEmailInstruction: '${msg("emailVerifyInstruction1",verifyEmail)}',
        submitText: '${msg("emailVerifyResend")}',
        // <#else>
        verifyEmailInstruction: '${msg("emailVerifyInstruction4",user.email)}',
        submitText: '${msg("emailVerifySend")}',
        // </#if>
      };
      window._l10n = {
        ...window._l10n,
        emailVerifyTitle: '${msg("emailVerifyTitle")}',
        emailVerifyInstruction2: '${msg("emailVerifyInstruction2")}',
        emailVerifyInstruction3: '${msg("emailVerifyInstruction3")}',
        doCancel: '${msg("doCancel")}',
        doClickHere: '${msg("doClickHere")}',
      }
    </script>
    <#elseif section = "ignore-header">
        ${msg("emailVerifyTitle")}
    <#elseif section = "ignore-form">
        <p class="instruction">
            <#if verifyEmail??>
                ${msg("emailVerifyInstruction1",verifyEmail)}
            <#else>
                ${msg("emailVerifyInstruction4",user.email)}
            </#if>
        </p>
        <#if isAppInitiatedAction??>
            <form id="kc-verify-email-form" class="${properties.kcFormClass!}" action="${url.loginAction}" method="post">
                <div class="${properties.kcFormGroupClass!}">
                    <div id="kc-form-buttons" class="${properties.kcFormButtonsClass!}">
                        <#if verifyEmail??>
                            <input class="${properties.kcButtonClass!} ${properties.kcButtonDefaultClass!} ${properties.kcButtonLargeClass!}" type="submit" value="${msg("emailVerifyResend")}" />
                        <#else>
                            <input class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonLargeClass!}" type="submit" value="${msg("emailVerifySend")}" />
                        </#if>
                        <button class="${properties.kcButtonClass!} ${properties.kcButtonDefaultClass!} ${properties.kcButtonLargeClass!}" type="submit" name="cancel-aia" value="true" formnovalidate/>${msg("doCancel")}</button>
                    </div>
                </div>
            </form>
        </#if>
    <#elseif section = "ignore-info">
        <#if !isAppInitiatedAction??>
            <p class="instruction">
                ${msg("emailVerifyInstruction2")}
                <br/>
                <a href="${url.loginAction}">${msg("doClickHere")}</a> ${msg("emailVerifyInstruction3")}
            </p>
        </#if>
    </#if>
</@layout.registrationLayout>
