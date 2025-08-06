<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=true displayMessage=!messagesPerField.existsError('username'); section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        attemptedUserName: '${(auth.attemptedUsername!)}',
        errors: {
          username: '${kcSanitize(messagesPerField.get("username"))?no_esc}',
        },
        loginUrl: '${url.loginUrl}',
      };
      window._l10n = {
        ...window._l10n,
        emailForgotTitle: '${msg("emailForgotTitle")}',
        username: '${msg("username")}',
        usernameOrEmail: '${msg("usernameOrEmail")}',
        email: '${msg("email")}',
        backToLogin: '${kcSanitize(msg("backToLogin"))?no_esc}',
        doSubmit: '${msg("doSubmit")}',
        emailInstructionUsername: '${msg("emailInstructionUsername")}',
        emailInstruction: '${msg("emailInstruction")}',
        forgotPasswordError: '${msg("forgotPasswordError")}'
      };
    </script>
    </#if>
</@layout.registrationLayout>
