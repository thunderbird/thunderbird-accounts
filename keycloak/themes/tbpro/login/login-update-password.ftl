<#import "template.ftl" as layout>
<#import "password-commons.ftl" as passwordCommons>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('password','password-confirm'); section>
<#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        errors: {
          password: '${kcSanitize(messagesPerField.get("password"))?no_esc}',
          passwordConfirm: '${kcSanitize(messagesPerField.get("password-confirm"))?no_esc}',
        },
      };
      window._l10n = {
        ...window._l10n,
        updatePasswordTitle: '${msg("updatePasswordTitle")}',
        password: '${msg("password")}',
        passwordConfirm: '${msg("passwordConfirm")}',
        passwordNew: '${msg("passwordNew")}',
        showPassword: '${msg("showPassword")}',
        hidePassword: '${msg("hidePassword")}',
        doSubmit: '${msg("doSubmit")}',
        doCancel: '${msg("doCancel")}',
        logoutOtherSessions: '${msg("logoutOtherSessions")}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
