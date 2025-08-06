<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('totp'); section>
<#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        errors: {
          totp: '${kcSanitize(messagesPerField.get("totp"))?no_esc}',
        },
        userOtpCredentials: [
          // This is formatted specifically for SelectInput from services-ui!
          //<#list otpLogin.userOtpCredentials as creds>
          {
            value: '${creds.id}',
            label: '${creds.userLabel}',
          },
          //</#list>
        ],
        selectedOtpCredential: '${otpLogin.selectedCredentialId}',
      };
      window._l10n = {
        ...window._l10n,
        doLogIn: '${msg("doLogIn")}',
        loginOtpOneTime: '${msg("loginOtpOneTime")}',
        loginTotpDeviceName: '${msg("loginTotpDeviceName")}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
