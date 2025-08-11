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
    </#if>
</@layout.registrationLayout>
