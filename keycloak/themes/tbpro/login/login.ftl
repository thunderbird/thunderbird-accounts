<#import "template.ftl" as layout>
<#import "passkeys.ftl" as passkeys>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction?js_string?no_esc}',
        supportUrl: '${properties.tbproContactUrl}',
        clientUrl: '${client.baseUrl}',
        // <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
        registerUrl: '${url.registrationUrl?js_string?no_esc}',
        // <#else>
        registerUrl: '${properties.tbproSignupUrl}',
        // </#if>
        // <#if realm.resetPasswordAllowed>
        forgotPasswordUrl: '${url.loginResetCredentialsUrl?js_string?no_esc}',
        // <#else>
        forgotPasswordUrl: null,
        // </#if>
        rememberMe: '${(login.rememberMe)!"off"}' === 'on',
        loginHint: '${login.username!''}',
        tbProPrimaryDomain: '${properties.tbproPrimaryDomain}',
        // Operator-entered realm overrides: passed as the {0} argument so MessageFormat never parses their quotes or
        // braces, and escaped for this JS string literal rather than HTML-escaped.
        noticeText: '${msg("{0}", r"${maintenanceNotice}")?js_string?no_esc}',
        noticeType: '${msg("{0}", r"${maintenanceNoticeType}")?js_string?no_esc}',
        noticeStatusUrl: '${msg("{0}", r"${maintenanceNoticeStatusUrl}")?js_string?no_esc}',
        noticeStatusText: '${msg("{0}", r"${maintenanceNoticeStatusText}")?js_string?no_esc}',
        socialProviders: [
            //<#if realm.password && social?? && social.providers?has_content>
            //<#list social.providers as p>
          {
            name: '${p.displayName!}',
            alias: '${p.alias}',
            loginUrl: '${p.loginUrl?js_string?no_esc}',
            iconName: '${properties.kcCommonLogoIdP!}',
            className: '${properties.kcFormSocialAccountNameClass!}',
          },
            //</#list>
            //</#if>
        ],
        firstError: '${kcSanitize(messagesPerField.getFirstError("username","password"))?no_esc}',
      };
      window._l10n = {
        ...window._l10n,
        loginAccountTitle: '${msg("loginAccountTitle")}',
        username: '${msg("username")}',
        usernameOrEmail: '${msg("usernameOrEmail")}',
        email: '${msg("email")}',
        password: '${msg("password")}',
        showPassword: '${msg("showPassword")}',
        hidePassword: '${msg("hidePassword")}',
        rememberMe: '${msg("rememberMe")}',
        noAccount: '${msg("noAccount")}',
        doLogIn: '${msg("doLogIn")}',
        doRegister: '${msg("doRegister")}',
        doForgotPassword: '${msg("doForgotPassword")}',
        identityProviderLoginLabel: '${msg("identity-provider-login-label")}',
        goToRegister: '${msg("goToRegister")}',
        goToRegisterAction: '${msg("goToRegisterAction")}',
        needHelp: '${msg("needHelp")}',
        needHelpAction: '${msg("needHelpAction")}',
        inviteOnly: '${msg("inviteOnly")}',
        inviteOnlyAction: '${msg("inviteOnlyAction")}',
        usernameDomainSuggestion: '${msg("usernameDomainSuggestion")}',
      };
    </script>
    </#if>

</@layout.registrationLayout>
