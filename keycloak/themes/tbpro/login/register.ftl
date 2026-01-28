<#import "template.ftl" as layout>
<#import "user-profile-commons.ftl" as userProfileCommons>
<#import "register-commons.ftl" as registerCommons>
<@layout.registrationLayout displayMessage=messagesPerField.exists('global') displayRequiredFields=true; section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.registrationAction}',
        messageHeader: '${kcSanitize(msg("${messageHeader!}"))?no_esc}',
        errors: {
          email: '${kcSanitize(messagesPerField.get("email"))?no_esc}',
          username: '${kcSanitize(messagesPerField.get("username"))?no_esc}',
          password: '${kcSanitize(messagesPerField.get("password"))?no_esc}',
          passwordConfirm: '${kcSanitize(messagesPerField.get("password-confirm"))?no_esc}',
        },
        clientUrl: '${client.baseUrl}',
        currentLocale: '${(locale.currentLanguageTag)!"en"}',
        tbProPrimaryDomain: '${properties.tbproPrimaryDomain}',
        attributes: {
          // Holds the profile values between page loads, attributes can technically have multi-values but registration does not.
          // For reference: https://github.com/keycloak/keycloak/blob/47b91b995dd3f2089bf15400fbcbe18ebd91f16e/themes/src/main/resources/theme/base/login/user-profile-commons.ftl
          //<#list profile.attributes as attribute>
          '${attribute.name}': '${(attribute.value)!""}',
          //</#list>
        },
      };
      window._l10n = {
        ...window._l10n,
        registerTitle: '${msg("registerTitle")}',
        username: '${msg("username")}',
        email: '${msg("email")}',
        password: '${msg("password")}',
        passwordConfirm: '${msg("passwordConfirm")}',
        showPassword: '${msg("showPassword")}',
        hidePassword: '${msg("hidePassword")}',
        backToLogin: '${kcSanitize(msg("backToLogin"))?no_esc}',
        doRegister: '${msg("doRegister")}',
        goToLogin: '${msg("goToLogin")}',
        goToLoginAction: '${msg("goToLoginAction")}',
        signUpUsernameSuffix: '${msg("signUpUsernameSuffix")}'.replaceAll('@', "{'@'}"),
        signUpUsernameHelp: '${msg("signUpUsernameHelp")}'.replaceAll('@', "{'@'}"),
        signUpPasswordHelp: '${msg("signUpPasswordHelp")}',
        signUpPasswordConfirmHelp: '${msg("signUpPasswordConfirmHelp")}',
        registerError: '${msg("registerError")}',
        recoveryEmail: '${msg("recoveryEmail")}',
        recoveryEmailHelp: '${msg("recoveryEmailHelp")}',
        invalidPasswordDoesntMatch: '${msg("invalidPasswordConfirmMessage")}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
