<script setup>
import { TextInput, PrimaryButton, SelectInput, LinkButton } from "@thunderbirdops/services-ui";
import { computed, ref, useTemplateRef } from "vue";
import MessageBar from '@kc/vue/components/MessageBar.vue';
import CancelForm from '@kc/vue/components/CancelForm.vue';

const errors = window._page.currentView?.errors;
const formAction = window._page.currentView?.formAction;
const userOtpCredentials = window._page.currentView?.userOtpCredentials;
const selectedOtpCredential = window._page.currentView?.selectedOtpCredential;
const showTryAnotherWay = window._page.currentView?.showTryAnotherWay === 'true';
const OtpCredentialModel = ref(selectedOtpCredential);
const loginForm = useTemplateRef('login-form');
const tryAnotherWayForm = useTemplateRef('try-another-way-form');

const onSubmit = () => {
  loginForm?.value?.submit();
};

const onTryAnotherWay = () => {
  tryAnotherWayForm?.value?.cancel();
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
        <!-- #1011: with a single credential there's nothing to choose, so hide the
             selector (matches stock Keycloak's `userOtpCredentials?size gt 1` guard). -->
        <select-input v-if="userOtpCredentials.length > 1" name="device-input" data-testid="device-input" :options="userOtpCredentials" v-model="OtpCredentialModel">{{
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

    <div class="try-another-way" v-if="showTryAnotherWay">
      <cancel-form ref="try-another-way-form" :action="formAction" cancel-name="tryAnotherWay" cancel-value="on"/>
      <link-button data-testid="try-another-way-btn" @click="onTryAnotherWay">{{ $t('doTryAnotherWay') }}</link-button>
    </div>
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

.try-another-way {
  margin-top: var(--space-12);
  display: flex;
  justify-content: center;
}
</style>
