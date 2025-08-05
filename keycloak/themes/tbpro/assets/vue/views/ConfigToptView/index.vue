<script setup>
import {
  TextInput,
  PrimaryButton,
  SecondaryButton,
  LinkButton,
  CheckboxInput,
  NoticeBar,
  CopyIcon,
} from "@thunderbirdops/services-ui";
import {computed, ref} from "vue";
import {i18n} from '@/composables/i18n.js';

const formAction = ref(window._page.currentView?.formAction);
const settingsForm = ref();
const cancelForm = ref();
const isManualMode = computed(() => window._page.currentView?.mode === 'manual');

const showCancel = computed(() => window._page.appInitiatedAction !== 'false');
const supportedApplications = ref(window._page.currentView?.supportedApplications ?? []);
const qrCodeSrc = computed(() => {
  return `data:image/png;base64, ${window._page.currentView?.loginTotp?.secretQrCode}`;
});
const manualUrl = ref(window._page.currentView?.loginTotp?.manualUrl);

const totpType = ref(window._page.currentView?.loginTotp?.type);
const totpTypeName = ref(window._page.currentView?.loginTotp?.typeName);

// Manual mode settings
const realmTitle = ref(window._page.realmTitle);
const username = ref(window._page.currentView?.loginTotp?.username);
const secretEncoded = ref(window._page.currentView?.loginTotp?.secretEncoded);
const secret = ref(window._page.currentView?.loginTotp?.secret);
const qrUrl = ref(window._page.currentView?.loginTotp?.qrUrl);
const algorithmKey = ref(window._page.currentView?.loginTotp?.algorithmKey);
const digits = ref(window._page.currentView?.loginTotp?.digits);
const period = ref(window._page.currentView?.loginTotp?.period);
const initialCounter = ref(window._page.currentView?.loginTotp?.initialCounter);

// new

const manualMode = ref(false);
/**
 * Forms a manual otpauth uri.
 * Keycloak seems to just spit out a list of values, so lets format those values into a nice uri recognized by most authenticators.
 * Ref: https://github.com/google/google-authenticator/wiki/Key-Uri-Format
 * Ref: https://www.ietf.org/archive/id/draft-linuxgemini-otpauth-uri-02.html
 */
const otpManualUrl = computed(() => {
  const queryParams = {
    secret: secretEncoded.value.replaceAll(' ', ''),
    algorithm: algorithmKey.value,
    digits: digits.value,
  }
  if (totpType === 'hotp') {
    queryParams['counter'] = initialCounter.value;
  } else {
    queryParams['period'] = period.value;
  }
  return encodeURI(`otpauth://${totpType.value}/${realmTitle.value}:${username.value}?${new URLSearchParams(queryParams)}`)
});

const myLinkShow = ref(false);
const myLinkTooltip = ref(i18n.t('copyTotp'));
// Messages

const message = ref(window._page.message);
const errors = ref(window._page.currentView?.errors);
const totpError = computed(() => {
  return errors.value?.totp === '' ? null : errors.value?.totp;
});
const userLabelError = computed(() => {
  return errors.value?.userLabel === '' ? null : errors.value?.userLabel;
});

const isCancelSubmit = ref(false);

const totpStep = ref(totpError.value || userLabelError.value ? 2 : 1);


const onSubmit = () => {
  settingsForm?.value?.submit();
};

const onCancel = () => {
  isCancelSubmit.value = true;
  // Need time for the ref to pick it up...
  // FIXME: This should be nicer...
  window.setTimeout(() => {
    cancelForm?.value?.submit();
  }, 100);
}

const copyLink = async () => {
  if (!navigator.clipboard?.writeText) {
    myLinkTooltip.value = i18n.t('copiedToClipboardError');
  } else {
    await navigator.clipboard?.writeText(otpManualUrl.value);
    myLinkTooltip.value = i18n.t('copiedToClipboard');
  }
  myLinkShow.value = true;

  // Fade out after a bit
  setTimeout(() => {
    myLinkShow.value = false;

    // After the animation fades...
    setTimeout(() => {
      myLinkTooltip.value = i18n.t('copyTotp');
    }, 500);
  }, 4000);
};

const onNext = () => {
  totpStep.value += 1;
  if (totpStep.value >= 3) {
    onSubmit();
  }
}
const onPrevious = () => {
  totpStep.value -= 1;

  if (totpStep.value <= 0) {
    onCancel();
  }
}
</script>

<script>
export default {
  name: 'ConfigTotpView'
}
</script>


<template>
  <div class="panel">
    <h2>{{ $t('loginTotpTitle') }}</h2>
    <notice-bar :type="message.type" v-if="message?.type">{{ message.summary }}</notice-bar>
    {{showCancel && isCancelSubmit}}
    <form id="kc-totp-cancel-form" ref="cancelForm" method="POST" :action="formAction" v-if="showCancel && isCancelSubmit">
        <input type="hidden" id="cancelTOTPBtn" name="cancel-aia" value="true"/>
    </form>

    <section v-if="totpStep === 1" id="totpStep1">
      <section class="split-view" v-if="!manualMode">
        <article>
          <h3>{{ $t('scanTotp1') }}</h3>
          <p>{{ $t('scanTotp2') }}</p>
          <h3>{{ $t('scanTotp3') }}</h3>
          <p>{{ $t('scanTotp4') }}</p>
        </article>
        <aside class="qr-container">
          <img :src="qrCodeSrc" :alt="$t('qrCode')"/>
          <link-button @click="() => manualMode = true" id="mode-manual">{{ $t('loginTotpUnableToScan') }}</link-button>
        </aside>
      </section>
      <section v-else>
        <article>
          <p>{{ $t('manualTotp1') }}</p>
        </article>
        <aside>
          <link-button class="my-link-btn" @click="copyLink" :tooltip="myLinkTooltip" :force-tooltip="myLinkShow">
            <template v-slot:icon>
              <copy-icon/>
            </template>
            {{ otpManualUrl }}
          </link-button>
          <link-button @click="() => manualMode = false" id="mode-barcode">{{
              $t('loginTotpScanBarcode')
            }}
          </link-button>
        </aside>
      </section>
      <div class="buttons">
        <primary-button class="submit" @click="onNext">{{ $t('doContinue') }}</primary-button>
        <secondary-button id="back" class="submit" @click="onPrevious" v-if="showCancel">{{
              $t('doCancel')
            }}
        </secondary-button>
      </div>
    </section>
    <section v-else-if="totpStep === 2" id="totpStep2">
      <form id="kc-totp-settings-form" ref="settingsForm" method="POST" :action="formAction" @submit.prevent="onSubmit"
            @keyup.enter="onSubmit">
        <p>{{ $t('labelTotp') }}</p>
        <div class="form-elements">
          <text-input id="totp" name="totp" required autocomplete="off" type="text" :error="totpError">
            {{ $t('authenticatorCode') }}
          </text-input>
          <text-input id="userLabel" name="userLabel" required autocomplete="off" type="text" :error="userLabelError">
            {{ $t('loginTotpDeviceName') }}
          </text-input>
          <checkbox-input id="logout-sessions" name="logout-sessions"
                          :label="$t('logoutOtherSessions')"></checkbox-input>
          <input type="hidden" id="totpSecret" name="totpSecret" :value="secret" />
        </div>
        <div class="buttons">
          <primary-button id="saveTOTPBtn" :value="$t('doSubmit')" class="submit" @click="onNext">{{ $t('doSubmit') }}</primary-button>
          <secondary-button id="back" class="submit" @click="onPrevious">{{
              $t('doBack')
            }}
          </secondary-button>
        </div>
      </form>
    </section>
    <!--
        <section>
          <p>{{ $t('loginTotpStep1') }}</p>
          <ul>
            <li v-for="app in supportedApplications">
              {{ app }}
            </li>
          </ul>
        </section>
        <template v-if="isManualMode">
          <section>
            <p>{{ $t('loginTotpManualStep2') }}</p>
            <p>{{ secretEncoded }}</p>
            <p><a :href="qrUrl" id="mode-barcode">{{ $t('loginTotpScanBarcode') }}</a></p>
          </section>
          <section>
            <p>{{ $t('loginTotpManualStep3') }}</p>
            <ul>
              <li id="kc-totp-type">{{ $t("loginTotpType") }}: {{ totpTypeName }}</li>
              <li id="kc-totp-algorithm">{{ $t("loginTotpAlgorithm") }}: {{ algorithmKey }}</li>
              <li id="kc-totp-digits">{{ $t("loginTotpDigits") }}: {{ digits }}</li>
              <li id="kc-totp-period" v-if="totpType === 'totp'">{{ $t("loginTotpInterval") }}: {{ period }}</li>
              <li id="kc-totp-counter" v-else-if="totpType === 'hotp'">{{ $t("loginTotpCounter") }}: {{
                  initialCounter
                }}
              </li>
            </ul>
          </section>
        </template>
        <section v-else>
          <p>{{ $t('loginTotpStep2') }}</p>
          <img :src="qrCodeSrc" :alt="$t('qrCode')"/>
          <p><a :href="manualUrl" id="mode-manual">{{ $t('loginTotpUnableToScan') }}</a></p>
        </section>
        <section>
          <p>{{ $t('loginTotpStep3') }}</p>
          <p>{{ $t('loginTotpStep3DeviceName') }}</p>
        </section>
    -->
  </div>

</template>

<style scoped>
.notice-bar {
  margin-bottom: var(--space-12);
}

.panel {
  margin: 30px
}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.split-view {
  display: flex;
  h3 {
    font-size: var(--txt-input);
  }
}

.qr-container {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;
}

  .my-link-btn {
    text-align: left !important;
    width: 100%;
  }

  :deep(.my-link-btn .text) {
    width: 100%;
    overflow: scroll;
    white-space: pre;
    padding-bottom: var(--txt-input);
  }

  :deep(.my-link-btn .icon) {
    padding-bottom: var(--txt-input);
  }
</style>
