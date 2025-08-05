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
    <#elseif section = "ignore-header">
        ${msg("loginTotpTitle")}
    <#elseif section = "ignore-form">
        <ol id="kc-totp-settings">
            <li>
                <p>${msg("loginTotpStep1")}</p>

                <ul id="kc-totp-supported-apps">
                    <#list totp.supportedApplications as app>
                        <li>${msg(app)}</li>
                    </#list>
                </ul>
            </li>

            <#if mode?? && mode = "manual">
                <li>
                    <p>${msg("loginTotpManualStep2")}</p>
                    <p><span id="kc-totp-secret-key">${totp.totpSecretEncoded}</span></p>
                    <p><a href="${totp.qrUrl}" id="mode-barcode">${msg("loginTotpScanBarcode")}</a></p>
                </li>
                <li>
                    <p>${msg("loginTotpManualStep3")}</p>
                    <p>
                    <ul>
                        <li id="kc-totp-type">${msg("loginTotpType")}: ${msg("loginTotp." + totp.policy.type)}</li>
                        <li id="kc-totp-algorithm">${msg("loginTotpAlgorithm")}: ${totp.policy.getAlgorithmKey()}</li>
                        <li id="kc-totp-digits">${msg("loginTotpDigits")}: ${totp.policy.digits}</li>
                        <#if totp.policy.type = "totp">
                            <li id="kc-totp-period">${msg("loginTotpInterval")}: ${totp.policy.period}</li>
                        <#elseif totp.policy.type = "hotp">
                            <li id="kc-totp-counter">${msg("loginTotpCounter")}: ${totp.policy.initialCounter}</li>
                        </#if>
                    </ul>
                    </p>
                </li>
            <#else>
                <li>
                    <p>${msg("loginTotpStep2")}</p>
                    <img id="kc-totp-secret-qr-code" src="data:image/png;base64, ${totp.totpSecretQrCode}" alt="Figure: Barcode"><br/>
                    <p><a href="${totp.manualUrl}" id="mode-manual">${msg("loginTotpUnableToScan")}</a></p>
                </li>
            </#if>
            <li>
                <p>${msg("loginTotpStep3")}</p>
                <p>${msg("loginTotpStep3DeviceName")}</p>
            </li>
        </ol>

        <form action="${url.loginAction}" class="${properties.kcFormClass!}" id="kc-totp-settings-form" method="post">
            <div class="${properties.kcFormGroupClass!}">
                <div class="${properties.kcInputWrapperClass!}">
                    <label for="totp" class="control-label">${msg("authenticatorCode")}</label> <span class="required">*</span>
                </div>
                <div class="${properties.kcInputWrapperClass!}">
                    <input type="text" id="totp" name="totp" autocomplete="off" class="${properties.kcInputClass!}"
                           aria-invalid="<#if messagesPerField.existsError('totp')>true</#if>"
                           dir="ltr"
                    />

                    <#if messagesPerField.existsError('totp')>
                        <span id="input-error-otp-code" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
                            ${kcSanitize(messagesPerField.get('totp'))?no_esc}
                        </span>
                    </#if>

                </div>
                <input type="hidden" id="totpSecret" name="totpSecret" value="${totp.totpSecret}" />
                <#if mode??><input type="hidden" id="mode" name="mode" value="${mode}"/></#if>
            </div>

            <div class="${properties.kcFormGroupClass!}">
                <div class="${properties.kcInputWrapperClass!}">
                    <label for="userLabel" class="control-label">${msg("loginTotpDeviceName")}</label> <#if totp.otpCredentials?size gte 1><span class="required">*</span></#if>
                </div>

                <div class="${properties.kcInputWrapperClass!}">
                    <input type="text" class="${properties.kcInputClass!}" id="userLabel" name="userLabel" autocomplete="off"
                           aria-invalid="<#if messagesPerField.existsError('userLabel')>true</#if>" dir="ltr"
                    />

                    <#if messagesPerField.existsError('userLabel')>
                        <span id="input-error-otp-label" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
                            ${kcSanitize(messagesPerField.get('userLabel'))?no_esc}
                        </span>
                    </#if>
                </div>
            </div>

            <div class="${properties.kcFormGroupClass!}">
                <@passwordCommons.logoutOtherSessions/>
            </div>

            <#if isAppInitiatedAction??>
                <input type="submit"
                       class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonLargeClass!}"
                       id="saveTOTPBtn" value="${msg("doSubmit")}"
                />
                <button type="submit"
                        class="${properties.kcButtonClass!} ${properties.kcButtonDefaultClass!} ${properties.kcButtonLargeClass!} ${properties.kcButtonLargeClass!}"
                        id="cancelTOTPBtn" name="cancel-aia" value="true" />${msg("doCancel")}
                </button>
            <#else>
                <input type="submit"
                       class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!} ${properties.kcButtonLargeClass!}"
                       id="saveTOTPBtn" value="${msg("doSubmit")}"
                />
            </#if>
        </form>
    </#if>
</@layout.registrationLayout>
