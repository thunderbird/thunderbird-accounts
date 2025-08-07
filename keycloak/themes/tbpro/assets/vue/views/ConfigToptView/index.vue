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
import { computed, ref, useTemplateRef } from "vue";
import { i18n } from '@/composables/i18n.js';
import CancelForm from '@/vue/components/CancelForm.vue';
import MessageBar from "@/vue/components/MessageBar.vue";

const isManualMode = ref(false);

const formAction = window._page.currentView?.formAction;
const settingsForm = useTemplateRef('settings-form');
const cancelForm = useTemplateRef('cancel-form');

const showCancel = computed(() => window._page.appInitiatedAction !== 'false');
const qrCodeSrc = computed(() => {
  return `data:image/png;base64, ${window._page.currentView?.loginTotp?.secretQrCode}`;
});

const totpType = window._page.currentView?.loginTotp?.type;
const realmTitle = window._page.realmTitle;
const username = window._page.currentView?.loginTotp?.username;
const secretEncoded = window._page.currentView?.loginTotp?.secretEncoded;
const secret = window._page.currentView?.loginTotp?.secret;
const algorithmKey = window._page.currentView?.loginTotp?.algorithmKey;
const digits = window._page.currentView?.loginTotp?.digits;
const period = window._page.currentView?.loginTotp?.period;
const initialCounter = window._page.currentView?.loginTotp?.initialCounter;

// Copy the otpauth link settings
const myLinkShow = ref(false);
const myLinkTooltip = ref(i18n.t('copyTotp'));

// Messages
const errors = window._page.currentView?.errors;
const totpError = computed(() => {
  return errors?.totp === '' ? null : errors?.totp;
});
const userLabelError = computed(() => {
  return errors?.userLabel === '' ? null : errors?.userLabel;
});


// If we have an error then start on step 2, otherwise show step 1
const totpStep = ref(totpError.value || userLabelError.value ? 2 : 1);

/**
 * Forms a manual otpauth uri.
 * Keycloak seems to just spit out a list of values, so lets format those values into a nice uri recognized by most authenticators.
 * Ref: https://github.com/google/google-authenticator/wiki/Key-Uri-Format
 * Ref: https://www.ietf.org/archive/id/draft-linuxgemini-otpauth-uri-02.html
 */
const otpManualUrl = computed(() => {
  const queryParams = {
    secret: secretEncoded.replaceAll(' ', ''),
    algorithm: algorithmKey,
    digits: digits,
  };
  if (totpType === 'hotp') {
    queryParams['counter'] = initialCounter;
  } else {
    queryParams['period'] = period;
  }
  return encodeURI(`otpauth://${totpType}/${realmTitle}:${username}?${new URLSearchParams(queryParams)}`);
});

const onSubmit = () => {
  settingsForm?.value?.submit();
};
const onCancel = () => {
  cancelForm?.value?.cancel();
};

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
};
const onPrevious = () => {
  totpStep.value -= 1;
  if (totpStep.value <= 0) {
    onCancel();
  }
};
</script>

<script>
export default {
  name: 'ConfigTotpView'
};
</script>


<template>
  <div class="panel">
    <h2>{{ $t('loginTotpTitle') }}</h2>
    <message-bar/>
    <cancel-form ref="cancel-form" :action="formAction" cancelId="cancelTOTPBtn" cancelValue="true"
                 cancelName="cancel-aia"/>

    <section v-if="totpStep === 1" id="totpStep1" data-testid="totp-step-2">
      <section class="split-view" v-if="!isManualMode">
        <article>
          <h3>{{ $t('scanTotp1') }}</h3>
          <p>{{ $t('scanTotp2') }}</p>
          <h3>{{ $t('scanTotp3') }}</h3>
          <p>{{ $t('scanTotp4') }}</p>
        </article>
        <aside class="qr-container">
          <img :src="qrCodeSrc" :alt="$t('qrCode')"/>
          <link-button data-testid="switch-to-manual-mode-btn" @click="() => isManualMode = true" id="mode-manual">{{
              $t('loginTotpUnableToScan')
            }}
          </link-button>
        </aside>
      </section>
      <section v-else>
        <article>
          <p>{{ $t('manualTotp1') }}</p>
        </article>
        <aside>
          <link-button data-testid="copy-otp-manual-url-btn" class="my-link-btn" @click="copyLink"
                       :tooltip="myLinkTooltip" :force-tooltip="myLinkShow">
            <template v-slot:icon>
              <copy-icon/>
            </template>
            {{ otpManualUrl }}
          </link-button>
          <link-button data-testid="switch-to-qrcode-mode-btn" @click="() => isManualMode = false" id="mode-barcode">{{
              $t('loginTotpScanBarcode')
            }}
          </link-button>
        </aside>
      </section>
      <div class="buttons">
        <primary-button data-testid="continue-btn" class="submit" @click="onNext">{{
            $t('doContinue')
          }}
        </primary-button>
        <secondary-button data-testid="cancel-btn" id="back" class="submit" @click="onPrevious" v-if="showCancel">{{
            $t('doCancel')
          }}
        </secondary-button>
      </div>
    </section>
    <section v-else-if="totpStep === 2" id="totpStep2" data-testid="totp-step-2">
      <form id="kc-totp-settings-form" ref="settings-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
            @keyup.enter="onSubmit">
        <p>{{ $t('labelTotp') }}</p>
        <div class="form-elements">
          <text-input data-testid="totp-input" id="totp" name="totp" required autocomplete="off" type="text"
                      :error="totpError">
            {{ $t('authenticatorCode') }}
          </text-input>
          <text-input data-testid="user-label-input" id="userLabel" name="userLabel" required autocomplete="off"
                      type="text" :error="userLabelError">
            {{ $t('loginTotpDeviceName') }}
          </text-input>
          <checkbox-input data-testid="logout-other-sessions-btn" id="logout-sessions" name="logout-sessions"
                          :label="$t('logoutOtherSessions')"></checkbox-input>
          <input type="hidden" id="totpSecret" name="totpSecret" :value="secret"/>
        </div>
        <div class="buttons">
          <primary-button data-testid="submit-btn" id="saveTOTPBtn" :value="$t('doSubmit')" class="submit"
                          @click="onNext">{{
              $t('doSubmit')
            }}
          </primary-button>
          <secondary-button data-testid="back-btn" id="back" class="submit" @click="onPrevious">{{
              $t('doBack')
            }}
          </secondary-button>
        </div>
      </form>
    </section>
  </div>

</template>

<style scoped>
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
  margin-bottom: var(--space-4);
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
