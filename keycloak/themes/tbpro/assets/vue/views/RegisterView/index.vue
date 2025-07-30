<script setup>
import { TextInput, PrimaryButton, CheckboxInput, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

const errors = ref(window._page.currentView?.errors);
const formAction = ref(window._page.currentView?.formAction);
const loginUrl = ref(window._page.currentView?.loginUrl);
const timezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC');
const locale = ref(window._page.currentView?.currentLocale);
const username = ref();
const email = computed(() => {
  return `${username.value}@thundermail.com`;
})

const usernameError = computed(() => {
  return errors.value?.username === '' ? null : errors.value?.username;
});
const passwordError = computed(() => {
  return errors.value?.password === '' ? null : errors.value?.password;
});
const passwordConfirmError = computed(() => {
  return errors.value?.passwordConfirm === '' ? null : errors.value?.passwordConfirm;
});
const recoveryEmailError = computed(() => {
  return errors.value?.email === '' ? null : errors.value?.email;
});

const registerForm = ref();

const onSubmit = () => {
  registerForm?.value?.submit();
};

</script>

<script>
export default {
  name: 'RegisterView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('registerTitle') }}</h2>
    <form id="kc-register-form" ref="registerForm" method="POST" :action="formAction"  @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar type="error" v-if="usernameError || passwordError || passwordConfirmError || recoveryEmailError">{{ $t('registerError') }}</notice-bar>
      <div class="form-elements">
        <text-input id="partialUsername" name="partialUsername" required autocomplete="username" :error="usernameError" :outerSuffix="$t('signUpUsernameSuffix')" :help="$t('signUpUsernameHelp')" v-model="username">{{ $t('username') }}</text-input>
        <text-input id="email" name="email" required autocomplete="email" :error="recoveryEmailError" :help="$t('recoveryEmailHelp')">{{ $t('recoveryEmail') }}</text-input>
        <text-input id="password" name="password" required autocomplete="new-password" type="password" :error="passwordError" :help="$t('signUpPasswordHelp')">{{ $t('password') }}</text-input>
        <text-input id="password-confirm" name="password-confirm" required autocomplete="confirm-password" type="password" :error="passwordConfirmError" :help="$t('signUpPasswordConfirmHelp')">{{ $t('passwordConfirm') }}</text-input>
        <!-- These fields are dynamically filled out -->
        <text-input id="username" name="username" type="hidden" v-model="email"></text-input>
        <text-input id="locale" name="locale" type="hidden" v-model="locale"></text-input>
        <text-input id="zoneinfo" name="zoneinfo" type="hidden" v-model="timezone"></text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit">{{ $t('doRegister') }}</primary-button>
      </div>
    </form>
    <template v-if="loginUrl">
      <i18n-t keypath="goToLogin" tag="p">
        <a :href="loginUrl">{{ $t('goToLoginAction') }}</a>
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

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>