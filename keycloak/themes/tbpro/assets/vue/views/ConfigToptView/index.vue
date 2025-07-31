<script setup>
import { TextInput, PrimaryButton, SecondaryButton, CheckboxInput, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

const formAction = ref(window._page.currentView?.formAction);
const settingsForm = ref();

const showCancel = computed(() => window._page.appInitiatedAction !== 'false');
const supportedApplications = ref(window._page.currentView?.supportedApplications ?? []);
const qrCodeSrc = computed(() => {
  return `data:image/png;base64, ${window._page.currentView?.loginTotp?.secretQrCode}`;
});
const manualUrl = ref(window._page.currentView?.loginTotp?.manualUrl);

const message = ref(window._page.message);
const errors = ref(window._page.currentView?.errors);
const totpError = computed(() => {
  return errors.value?.totp === '' ? null : errors.value?.totp;
});
const userLabelError = computed(() => {
  return errors.value?.userLabel === '' ? null : errors.value?.userLabel;
});

const isCancelSubmit = ref(false);

const onSubmit = () => {
  settingsForm?.value?.submit();
};

const onCancel = () => {
  isCancelSubmit.value = true;
  onSubmit();
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

    <section>
      <p>{{ $t('loginTotpStep1') }}</p>
      <ul>
        <li v-for="app in supportedApplications">
          {{ app }}
        </li>
      </ul>
    </section>
    <section>
      <p>{{ $t('loginTotpStep2') }}</p>
      <img :src="qrCodeSrc" :alt="$t('qrCode')"/>
      <p><a :href="manualUrl" id="mode-manual">{{ $t('loginTotpUnableToScan') }}</a></p>
    </section>
    <section>
      <p>{{ $t('loginTotpStep3') }}</p>
      <p>{{ $t('loginTotpStep3DeviceName') }}</p>
    </section>
    <form id="kc-totp-settings-form" ref="settingsForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <div class="form-elements">
        <text-input id="totp" name="totp" required autocomplete="off" type="text" :error="totpError">{{ $t('authenticatorCode') }}</text-input>
        <text-input id="userLabel" name="userLabel" required autocomplete="off" type="text" :error="userLabelError">{{ $t('loginTotpDeviceName') }}</text-input>
        <checkbox-input id="logout-sessions" name="logout-sessions" :label="$t('logoutOtherSessions')"></checkbox-input>
       </div>
      <div class="buttons">
        <input v-if="isCancelSubmit" type="hidden" name="cancel-aia" value="true"/>
        <primary-button class="submit" @click="onSubmit">{{ $t('doSubmit') }}</primary-button>
        <secondary-button id="cancel" class="submit" @click="onCancel" v-if="showCancel">{{ $t('doCancel') }}</secondary-button>
      </div>
    </form>
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

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;
}
</style>