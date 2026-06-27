<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('recoveryCodeInput'); section>
<#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction?no_esc}',
        recoveryCodePrompt: '${msg("auth-recovery-code-prompt", recoveryAuthnCodesInputBean.codeNumber?c)?js_string}',
        showTryAnotherWay: '${(auth?has_content && auth.showTryAnotherWayLink())?c}',
        errors: {
          recoveryCodeInput: '${kcSanitize(messagesPerField.get("recoveryCodeInput"))?no_esc}',
        },
      };
      window._l10n = {
        ...window._l10n,
        doLogIn: '${msg("doLogIn")}',
        authRecoveryCodeHeader: '${msg("auth-recovery-code-header")?js_string}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
