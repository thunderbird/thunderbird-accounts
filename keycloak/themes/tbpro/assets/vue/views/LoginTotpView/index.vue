<script setup>
import { TextInput, PrimaryButton, SelectInput, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

const message = ref(window._page.message);
const errors = ref(window._page.currentView?.errors);
const formAction = ref(window._page.currentView?.formAction);
const userOtpCredentials = ref(window._page.currentView?.userOtpCredentials);
const selectedOtpCredential = ref(window._page.currentView?.selectedOtpCredential);
const OtpCredentialModel = ref(selectedOtpCredential.value);
const loginForm = ref();

const onSubmit = () => {
  loginForm?.value?.submit();
};

const totpError = computed(() => {
  return errors.value?.totp !== '' ? errors.value?.totp : null;
});

</script>

<script>
export default {
  name: 'LoginTotpView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('doLogIn') }}</h2>
    <form id="kc-form-login" ref="loginForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar :type="message.type" v-if="message?.type">{{ message.summary }}</notice-bar>
      <div class="form-elements">
        <select-input :options="userOtpCredentials" v-model="OtpCredentialModel">{{ $t('loginTotpDeviceName') }}</select-input>
        <text-input id="otp" name="otp" autocomplete="one-time-code" required autofocus :error="totpError">{{ $t('loginOtpOneTime') }}</text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit">{{ $t('doLogIn') }}</primary-button>
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

.post-password-options {
  display: flex;
  flex-direction: row;
  justify-content: space-between;

  .wrapper {
    padding-top: 21px;
  }

  a {
    padding-top: 4px;
    white-space: nowrap;
  }
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>
