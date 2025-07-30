<script setup>
import { TextInput, PrimaryButton, CheckboxInput, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

const formAction = ref(window._page.currentView?.formAction);
const updatePasswordForm = ref();

const message = ref(window._page.message);
const errors = ref(window._page.currentView?.errors);
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
    <form id="kc-passwd-update-form" ref="updatePasswordForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar :type="message.type" v-if="message?.type">{{ message.summary }}</notice-bar>
      <div class="form-elements">
        <text-input id="password-new" name="password-new" required autocomplete="new-password" type="password" :error="passwordError">{{ $t('password') }}</text-input>
        <text-input id="password-confirm" name="password-confirm" required autocomplete="confirm-password" type="password" :error="passwordConfirmError">{{ $t('passwordConfirm') }}</text-input>
        <checkbox-input id="logout-sessions" name="logout-sessions" :label="$t('logoutOtherSessions')"></checkbox-input>
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