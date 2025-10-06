<script setup>
import { TextInput, PrimaryButton, NoticeBar, NoticeBarTypes } from "@thunderbirdops/services-ui";
import { computed, useTemplateRef } from 'vue';
import MessageBar from '@/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@/svg/thunderbird-pro-light.svg';

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
  <div class="forgot-password-view-container">
    <a :href="clientUrl" class="logo-link">
      <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
    </a>

    <h2>{{ $t('emailForgotTitle') }}</h2>
    <form id="kc-reset-password-form" ref="reset-password-form" method="POST" :action="formAction"
          @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar :type="NoticeBarTypes.Critical" v-if="usernameError">{{ $t('forgotPasswordError') }}</notice-bar>
      <message-bar v-else/>
      <div class="form-elements">
        <text-input id="username" name="username" required autocomplete="username" autofocus v-model="username"
                    :help="$t('emailInstruction')" :error="usernameError">{{ $t('email') }}
        </text-input>
      </div>
      <div class="buttons">
        <template v-if="loginUrl">
          <a :href="loginUrl" data-testid="back-url">{{ $t('backToLogin') }}</a>
        </template>
  
        <primary-button class="submit" @click="onSubmit" data-testid="submit">{{ $t('doSubmit') }}</primary-button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.forgot-password-view-container {
  padding: 2rem;
}

h2 {
  font-size: 1.5rem;
  font-family: metropolis;
  font-weight: normal;
  line-height: 1.1;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
}

.logo-link {
  display: block;
  text-decoration: none;
  margin-block-end: 2.8125rem;

  .logo {
    height: 36px;
    width: auto;
    transition: opacity 0.2s ease;

    &:hover {
      opacity: 0.8;
    }
  }
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

@media (min-width: 1280px) {
  .forgot-password-view-container {
    padding: 6rem 10rem 5.625rem 6rem;
  }
}
</style>
