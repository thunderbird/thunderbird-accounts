<script setup>
import { TextInput, PrimaryButton, CheckboxInput, NoticeBar } from "@thunderbirdops/services-ui";
import { ref, computed } from "vue";

const errors = ref(window._page.currentView?.errors);
const formAction = ref(window._page.currentView?.formAction);
const loginUrl = window._page.currentView?.loginUrl;
const username = ref(window._page.currentView?.attemptedUserName);
const resetPasswordForm = ref();


const onSubmit = () => {
  resetPasswordForm?.value?.submit();
};
const usernameError = computed(() => {
  return errors.value?.username === '' ? null : errors.value?.username;
});

</script>

<script>
export default {
  name: 'ForgotPasswordView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('emailForgotTitle') }}</h2>
    <form id="kc-reset-password-form" ref="resetPasswordForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar type="error" v-if="usernameError">{{ $t('forgotPasswordError') }}</notice-bar>
      <div class="form-elements">
        <text-input id="username" name="username" required autocomplete="username" autofocus v-model="username" :help="$t('emailInstruction')" :error="usernameError">{{ $t('email') }}</text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit">{{ $t('doSubmit') }}</primary-button>
      </div>
    </form>
    <template v-if="loginUrl">
      <a :href="loginUrl">{{ $t('backToLogin') }}</a>
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

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>