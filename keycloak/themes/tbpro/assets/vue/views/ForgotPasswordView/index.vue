<script setup>
import { TextInput, PrimaryButton, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, useTemplateRef } from 'vue';
import MessageBar from '@/vue/components/MessageBar.vue';

const errors = window._page.currentView?.errors;
const formAction = window._page.currentView?.formAction;
const loginUrl = window._page.currentView?.loginUrl;
const username = window._page.currentView?.attemptedUserName;
const resetPasswordForm = useTemplateRef('reset-password-form');


const onSubmit = () => {
  resetPasswordForm?.value?.submit();
};
const usernameError = computed(() => {
  return errors?.username === '' ? null : errors?.username;
});

</script>

<script>
export default {
  name: 'ForgotPasswordView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('emailForgotTitle') }}</h2>
    <form id="kc-reset-password-form" ref="reset-password-form" method="POST" :action="formAction"
          @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar type="error" v-if="usernameError">{{ $t('forgotPasswordError') }}</notice-bar>
      <message-bar v-else/>
      <div class="form-elements">
        <text-input id="username" name="username" required autocomplete="username" autofocus v-model="username"
                    :help="$t('emailInstruction')" :error="usernameError">{{ $t('email') }}
        </text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit" data-testid="submit">{{ $t('doSubmit') }}</primary-button>
      </div>
    </form>
    <template v-if="loginUrl">
      <a :href="loginUrl" data-testid="back-url">{{ $t('backToLogin') }}</a>
    </template>
  </div>
</template>

<style scoped>
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
