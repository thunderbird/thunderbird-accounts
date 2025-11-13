<#import "template.ftl" as layout>
<#import "passkeys.ftl" as passkeys>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        supportUrl: '${client.baseUrl}contact/',
        clientUrl: '${client.baseUrl}',
        // <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
        registerUrl: '${url.registrationUrl}',
        // <#else>
        registerUrl: null,
        // </#if>
        // <#if realm.resetPasswordAllowed>
        forgotPasswordUrl: '${url.loginResetCredentialsUrl}',
        // <#else>
        forgotPasswordUrl: null,
        // </#if>
        rememberMe: '${(login.rememberMe)!"off"}' === 'on',
        socialProviders: [
            //<#if realm.password && social?? && social.providers?has_content>
            //<#list social.providers as p>
          {
            name: '${p.displayName!}',
            alias: '${p.alias}',
            loginUrl: '${p.loginUrl}',
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
      };
    </script>
    </#if>

</@layout.registrationLayout>
