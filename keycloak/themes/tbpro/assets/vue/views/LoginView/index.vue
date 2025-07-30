<script setup>
import { TextInput, PrimaryButton, CheckboxInput, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

const message = ref(window._page.message);
const errors = ref(window._page.currentView?.errors);
const firstError = ref(window._page.currentView?.firstError);
const formAction = ref(window._page.currentView?.formAction);
const rememberMe = ref(window._page.currentView?.rememberMe);
const forgotPasswordUrl = window._page.currentView?.forgotPasswordUrl;
const registerUrl = window._page.currentView?.registerUrl;
const loginForm = ref();

const onSubmit = () => {
  loginForm?.value?.submit();
};

const usernameError = computed(() => {
  return firstError.value !== '' ? '' : null;
});
const passwordError = computed(() => {
  return firstError.value !== '' ? '' : null;
});

</script>

<script>
export default {
  name: 'LoginView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('loginAccountTitle') }}</h2>
    <form id="kc-form-login" ref="loginForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar type="error" v-if="firstError">{{ firstError }}</notice-bar>
      <notice-bar type="error" v-if="message?.type === 'error'">{{ message.summary }}</notice-bar>
      <notice-bar type="success" v-if="message?.type === 'success'">{{ message.summary }}</notice-bar>
      <div class="form-elements">
        <text-input id="username" name="username" required autocomplete="username webauthn" autofocus :error="usernameError">{{ $t('email') }}</text-input>
        <text-input id="password" name="password" required autocomplete="current-password" type="password" :error="passwordError">{{ $t('password') }}</text-input>
      </div>
      <div class="post-password-options">
        <checkbox-input name="keep-me-signed-in" :label="$t('rememberMe')" v-model="rememberMe"></checkbox-input>
        <a v-if="forgotPasswordUrl" :href="forgotPasswordUrl">{{ $t('doForgotPassword') }}</a>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit">{{ $t('doLogIn') }}</primary-button>
      </div>
    </form>
    <template v-if="registerUrl">
      <i18n-t keypath="goToRegister" tag="p">
        <a :href="registerUrl">{{ $t('goToRegisterAction') }}</a>
      </i18n-t>

    </template>
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