<script setup lang="ts">
import { ref, computed, useTemplateRef } from 'vue';
import { TextInput, BrandButton, CheckboxInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhArrowRight } from '@phosphor-icons/vue';
import { TBPRO_WAIT_LIST } from '@kc/defines';

const firstError = window._page.currentView?.firstError;
const formAction = window._page.currentView?.formAction;
const rememberMe = window._page.currentView?.rememberMe;
const forgotPasswordUrl = window._page.currentView?.forgotPasswordUrl;
const supportUrl = window._page.currentView?.supportUrl;
const loginForm = useTemplateRef('login-form');
const message = window._page?.message;
const tbProPrimaryDomain = window._page.currentView?.tbProPrimaryDomain;

const onSubmit = () => {
  if (loginForm.value.checkValidity()) {
    loginForm?.value?.submit();
  }
};

const usernameError = computed(() => {
  return firstError ? '' : null;
});
const passwordError = computed(() => {
  return firstError ? '' : null;
});

// CheckboxInput requires a valid ref as a model to show the check icon
const rememberMeChecked = ref(rememberMe);
const username = ref(window._page.currentView?.loginHint);
const showUsernameHelpText = ref(false);
const usernameLocalPart = ref('');

const suggestedUsername = computed(() => `${usernameLocalPart.value}@${tbProPrimaryDomain}`);

const onUsernameBlur = (e: Event) => {
  const inputValue = (e.target as HTMLInputElement).value.toLowerCase();
  const [localPart, domain] = inputValue.split('@');

  usernameLocalPart.value = localPart;
  showUsernameHelpText.value = localPart && (!domain || domain !== tbProPrimaryDomain);
};

const onUsernameHelpTextClick = () => {
  username.value = suggestedUsername.value;
  showUsernameHelpText.value = false;
};

defineProps<{
  hidePassword: boolean;
}>();
</script>

<script lang="ts">
export default {
  name: 'LoginView',
};
</script>

<template>
  <notice-bar :type="NoticeBarTypes.Critical" v-if="firstError" class="notice-bar-login">{{ firstError }}</notice-bar>
  <notice-bar :type="NoticeBarTypes.Info" v-else-if="!message?.type" class="notice-bar-login">
    <i18n-t keypath="inviteOnly" tag="span">
      <a :href="TBPRO_WAIT_LIST" data-testid="go-to-invite-only-url" target="_blank">{{ $t('inviteOnlyAction') }}</a>
    </i18n-t>
  </notice-bar>

  <h2 data-testid="header-text">{{ $t('loginAccountTitle') }}</h2>
  <form
    id="kc-form-login"
    ref="login-form"
    method="POST"
    :action="formAction"
    @submit.prevent="onSubmit"
    @keyup.enter="onSubmit"
  >
    <div class="form-elements">
      <div>
        <text-input
          data-testid="username-input"
          id="username"
          name="username"
          required
          autocomplete="username webauthn"
          autofocus
          :error="usernameError"
          v-model="username"
          @blur="onUsernameBlur"
        >
          {{ $t('email') }}
        </text-input>
        <div aria-live="polite">
          <i18n-t v-if="showUsernameHelpText" class="username-help-text" keypath="usernameDomainSuggestion" tag="p">
            <button
              ref="username-suggestion-btn"
              type="button"
              data-testid="username-suggestion-btn"
              @click="onUsernameHelpTextClick"
            >
              {{ suggestedUsername }}
            </button>
          </i18n-t>
        </div>
      </div>
      <text-input
        v-if="!hidePassword"
        data-testid="password-input"
        id="password"
        name="password"
        required
        autocomplete="current-password"
        type="password"
        :error="passwordError"
      >
        {{ $t('password') }}
      </text-input>
    </div>

    <a v-if="forgotPasswordUrl && !hidePassword" :href="forgotPasswordUrl" class="forgot-password-link">
      {{ $t('doForgotPassword') }}
    </a>

    <checkbox-input
      data-testid="remember-me-input"
      name="keep-me-signed-in"
      :label="$t('rememberMe')"
      v-model="rememberMeChecked"
    ></checkbox-input>

    <div class="buttons">
      <brand-button data-testid="submit-btn" class="submit" @click="onSubmit">
        {{ $t('doLogIn') }}

        <template #iconRight>
          <ph-arrow-right size="20" />
        </template>
      </brand-button>
    </div>
  </form>
  <div class="footer-link-container">
    <!--
    <template v-if="registerUrl">
      <i18n-t keypath="goToRegister" tag="span">
        <a :href="registerUrl" data-testid="go-to-register-url">{{ $t('goToRegisterAction') }}</a>
      </i18n-t>
    </template>
    -->
    <i18n-t keypath="needHelp" tag="span">
      <a :href="supportUrl" data-testid="go-to-support-url">{{ $t('needHelpAction') }}</a>
    </i18n-t>
  </div>
</template>

<style scoped>
.notice-bar-login {
  margin-bottom: 1.5rem;
}

h2 {
  font-size: 2.25rem;
  font-family: metropolis;
  font-weight: normal;
  letter-spacing: -0.36px;
  line-height: 1.2;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
}

form {
  margin-block-end: 2.625rem;
}

.forgot-password-link {
  display: inline-block;
  font-size: 0.6875rem;
  color: var(--colour-ti-muted);
  margin-block-end: 2rem;
}

.footer-link-container {
  display: flex;
  gap: 0.425rem;
  flex-wrap: wrap;
  justify-content: flex-end;
  font-size: 0.75rem;
  color: var(--colour-ti-secondary);

  a {
    color: var(--colour-ti-secondary);
  }
}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 0.5rem;

  .username-help-text {
    font-size: 0.6875rem;
    color: var(--colour-ti-muted);
    margin-block: 0.5rem 0;

    button {
      all: unset;
      color: var(--colour-primary-default);
      text-decoration: underline;
      cursor: pointer;

      &:focus-visible {
        outline: 2px solid var(--colour-primary-default);
        outline-offset: 2px;
      }
    }
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
