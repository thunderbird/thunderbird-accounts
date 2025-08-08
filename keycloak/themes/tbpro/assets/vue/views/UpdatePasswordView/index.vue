<script setup>
import { TextInput, PrimaryButton, CheckboxInput } from "@thunderbirdops/services-ui";
import { computed, useTemplateRef } from 'vue';
import MessageBar from '@/vue/components/MessageBar.vue';

const formAction = window._page.currentView?.formAction;
const updatePasswordForm = useTemplateRef('update-password-form');

const errors = window._page.currentView?.errors;
const passwordError = computed(() => {
  return errors.value?.password === '' ? null : errors.value?.password;
});
const passwordConfirmError = computed(() => {
  return errors.value?.passwordConfirm === '' ? null : errors.value?.passwordConfirm;
});

const onSubmit = () => {
  updatePasswordForm?.value?.submit();
};
</script>

<script>
export default {
  name: 'UpdatePasswordView'
}
</script>


<template>
  <div class="panel">
    <h2>{{ $t('updatePasswordTitle') }}</h2>
    <form id="kc-passwd-update-form" ref="update-password-form" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <message-bar/>
      <div class="form-elements">
        <text-input data-testid="password-new-input" id="password-new" name="password-new" required autocomplete="new-password" type="password" :error="passwordError">{{ $t('password') }}</text-input>
        <text-input data-testid="password-confirm-input" id="password-confirm" name="password-confirm" required autocomplete="confirm-password" type="password" :error="passwordConfirmError">{{ $t('passwordConfirm') }}</text-input>
        <checkbox-input data-testid="logout-all-sessions-input" id="logout-sessions" name="logout-sessions" :label="$t('logoutOtherSessions')"></checkbox-input>
       </div>
      <div class="buttons">
        <primary-button data-testid="submit-btn" class="submit" @click="onSubmit">{{ $t('doSubmit') }}</primary-button>
      </div>
    </form>
    <template v-if="loginUrl">
      <a :href="loginUrl">{{ $t('backToLogin') }}</a>
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
