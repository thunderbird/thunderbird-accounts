<#import "template.ftl" as layout>
<#import "password-commons.ftl" as passwordCommons>
<@layout.registrationLayout displayRequiredFields=false displayMessage=!messagesPerField.existsError('totp','userLabel'); section>
    <#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        errors: {
          totp: '${kcSanitize(messagesPerField.get("totp"))?no_esc}',
          userLabel: '${kcSanitize(messagesPerField.get("userLabel"))?no_esc}',
        },
        supportedApplications: [
            //<#list totp.supportedApplications as app>
            '${msg(app)}',
            //</#list>
        ],
        mode: '${mode!}',
        loginTotp: {
          username: '${totp.username}',
          type: '${totp.policy.type}',
          typeName: '${msg("loginTotp." + totp.policy.type)}',
          secret: '${totp.totpSecret}',
          // if mode?? && mode == "manual"
          //secretQrCode: null,
          //manualUrl: null,
          secretEncoded: '${totp.totpSecretEncoded}',
          qrUrl: '${totp.qrUrl?no_esc}',
          algorithmKey: '${totp.policy.getAlgorithmKey()}',
          digits: '${totp.policy.digits}',
          period: '${totp.policy.period}',
          initialCounter: '${totp.policy.initialCounter}',
          // else
          secretQrCode: '${totp.totpSecretQrCode}',
          manualUrl: '${totp.manualUrl?no_esc}',
          //secretEncoded: null,
          //qrUrl: null,
          //algorithmKey: null,
          //digits: null,
          //period: null,
          //initialCounter: null,
          // /if
        }
      };
      window._l10n = {
        ...window._l10n,
        loginTotpTitle: '${msg("loginTotpTitle")}',
        loginTotpStep1: '${msg("loginTotpStep1")}',
        loginTotpStep2: '${msg("loginTotpStep2")}',
        loginTotpStep3: '${msg("loginTotpStep3")}',
        loginTotpStep3DeviceName: '${msg("loginTotpStep3DeviceName")}',
        loginTotpManualStep2: '${msg("loginTotpManualStep2")}',
        loginTotpManualStep3: '${msg("loginTotpManualStep3")}',
        loginTotpScanBarcode: '${msg("loginTotpScanBarcode")}',
        loginTotpType: '${msg("loginTotpType")}',
        loginTotpAlgorithm: '${msg("loginTotpAlgorithm")}',
        loginTotpDigits: '${msg("loginTotpDigits")}',
        loginTotpInterval: '${msg("loginTotpInterval")}',
        loginTotpCounter: '${msg("loginTotpCounter")}',
        loginTotpUnableToScan: '${msg("loginTotpUnableToScan")}',
        loginTotpDeviceName: '${msg("loginTotpDeviceName")}',
        authenticatorCode: '${msg("authenticatorCode")}',
        qrCode: '${msg("qrCode")}',
        logoutOtherSessions: '${msg("logoutOtherSessions")}',
        doSubmit: '${msg("doSubmit")}',
        doCancel: '${msg("doCancel")}',
        doContinue: '${msg("doContinue")}',
        doBack: '${msg("doBack")}',
        // custom messages
        scanTotp1: '${msg("scanTotp1")}',
        scanTotp2: '${msg("scanTotp2")}',
        scanTotp3: '${msg("scanTotp3")}',
        scanTotp4: '${msg("scanTotp4")}',
        manualTotp1: '${msg("manualTotp1")}',
        labelTotp: '${msg("labelTotp")?no_esc}',
        copyTotp: '${msg("copyTotp")}',
        copiedToClipboard: '${msg("copiedToClipboard")}',
        copiedToClipboardError: '${msg("copiedToClipboardError")}',

      };
    </script>
    </#if>
</@layout.registrationLayout>
