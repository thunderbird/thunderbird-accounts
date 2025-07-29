<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=true displayMessage=!messagesPerField.existsError('username'); section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
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
      };
    </script>
    <#elseif section = "header">
        ${msg("emailForgotTitle")}
    <#elseif section = "form">
        <form id="kc-reset-password-form" class="${properties.kcFormClass!}" action="${url.loginAction}" method="post">
            <div class="${properties.kcFormGroupClass!}">
                <div class="${properties.kcLabelWrapperClass!}">
                    <label for="username" class="${properties.kcLabelClass!}"><#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if></label>
                </div>
                <div class="${properties.kcInputWrapperClass!}">
                    <input type="text" id="username" name="username" class="${properties.kcInputClass!}" autofocus value="${(auth.attemptedUsername!'')}" aria-invalid="<#if messagesPerField.existsError('username')>true</#if>" dir="ltr"/>
                    <#if messagesPerField.existsError('username')>
                        <span id="input-error-username" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
                                    ${kcSanitize(messagesPerField.get('username'))?no_esc}
                        </span>
                    </#if>
                </div>
            </div>
            <div class="${properties.kcFormGroupClass!} ${properties.kcFormSettingClass!}">
                <div id="kc-form-options" class="${properties.kcFormOptionsClass!}">
                    <div class="${properties.kcFormOptionsWrapperClass!}">
                        <span><a href="${url.loginUrl}">${kcSanitize(msg("backToLogin"))?no_esc}</a></span>
                    </div>
                </div>

                <div id="kc-form-buttons" class="${properties.kcFormButtonsClass!}">
                    <input class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!} ${properties.kcButtonLargeClass!}" type="submit" value="${msg("doSubmit")}"/>
                </div>
            </div>
        </form>
    <#elseif section = "info" >
        <#if realm.duplicateEmailsAllowed>
            ${msg("emailInstructionUsername")}
        <#else>
            ${msg("emailInstruction")}
        </#if>
    </#if>
</@layout.registrationLayout>
