<script setup>
import { TextInput, PrimaryButton, SelectInput } from "@thunderbirdops/services-ui";
import { computed, ref, useTemplateRef } from "vue";
import MessageBar from '@/vue/components/MessageBar.vue';

const errors = window._page.currentView?.errors;
const formAction = window._page.currentView?.formAction;
const userOtpCredentials = window._page.currentView?.userOtpCredentials;
const selectedOtpCredential = window._page.currentView?.selectedOtpCredential;
const OtpCredentialModel = ref(selectedOtpCredential);
const loginForm = useTemplateRef('login-form');

const onSubmit = () => {
  loginForm?.value?.submit();
};

const totpError = computed(() => {
  return errors?.totp !== '' ? errors?.totp : null;
});

</script>

<script>
export default {
  name: 'LoginTotpView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('doLogIn') }}</h2>
    <form id="kc-form-login" ref="login-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
          @keyup.enter="onSubmit">
      <message-bar/>
      <div class="form-elements">
        <select-input name="device-input" data-testid="device-input" :options="userOtpCredentials" v-model="OtpCredentialModel">{{
            $t('loginTotpDeviceName')
          }}
        </select-input>
        <text-input data-testid="otp-input" id="otp" name="otp" autocomplete="one-time-code" required autofocus :error="totpError">
          {{ $t('loginOtpOneTime') }}
        </text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit" data-testid="submit-btn">{{ $t('doLogIn') }}</primary-button>
      </div>
    </form>
  </div>
</template>

<style scoped>
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
