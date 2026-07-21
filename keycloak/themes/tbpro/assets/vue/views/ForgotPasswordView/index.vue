<script setup lang="ts">
import { TextInput, PrimaryButton, NoticeBar, NoticeBarTypes } from "@thunderbirdops/services-ui";
import { ref, computed, useTemplateRef } from 'vue';
import { submitKeycloakForm } from '@kc/vue/keycloakForm';

const errors = window._page.currentView?.errors;
const formAction = window._page.currentView?.formAction;
const loginUrl = window._page.currentView?.loginUrl;
const username = window._page.currentView?.attemptedUserName;
const resetPasswordForm = useTemplateRef('reset-password-form');

const onSubmit = () => {
  if (resetPasswordForm.value.checkValidity()) {
    submitKeycloakForm(resetPasswordForm?.value);
  }
};

const usernameRef = ref(username);
const usernameError = computed(() => {
  return errors?.username === '' ? null : errors?.username;
});

</script>

<script lang="ts">
export default {
  name: 'ForgotPasswordView'
};
</script>

<template>
  <notice-bar :type="NoticeBarTypes.Critical" v-if="usernameError">{{ $t('forgotPasswordError') }}</notice-bar>

  <h2>{{ $t('emailForgotTitle') }}</h2>
  <form
    v-if="formAction"
    id="kc-reset-password-form"
    ref="reset-password-form"
    method="POST"
    :action="formAction"
    @submit.prevent="onSubmit" @keyup.enter="onSubmit"
  >
    <div class="form-elements">
      <text-input
        data-testid="username-input"
        id="username"
        name="username"
        required
        autocomplete="username"
        autofocus
        v-model="usernameRef"
        :help="$t('emailInstruction')"
        :error="usernameError"
      >
        {{ $t('email') }}
      </text-input>
    </div>
    <div class="buttons">
      <template v-if="loginUrl">
        <primary-button variant="outline" :href="loginUrl" data-testid="back-url">{{ $t('backToLogin') }}</primary-button>
      </template>

      <primary-button class="submit" @click="onSubmit" data-testid="submit">{{ $t('doSubmit') }}</primary-button>
    </div>
  </form>
</template>

<style scoped>
h2 {
  font-size: 1.5rem;
  font-family: metropolis;
  font-weight: normal;
  line-height: 1.1;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.buttons {
  display: flex;
  align-items: center;
  margin-top: var(--space-24);

  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>
