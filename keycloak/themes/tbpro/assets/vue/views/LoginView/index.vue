<script setup>
import { ref, computed, useTemplateRef } from 'vue';
import { TextInput, BrandButton, CheckboxInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhArrowRight } from '@phosphor-icons/vue';
import MessageBar from '@/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@/svg/thunderbird-pro-light.svg';

const firstError = window._page.currentView?.firstError;
const formAction = window._page.currentView?.formAction;
const rememberMe = window._page.currentView?.rememberMe;
const forgotPasswordUrl = window._page.currentView?.forgotPasswordUrl;
const registerUrl = window._page.currentView?.registerUrl;
const supportUrl = window._page.currentView?.supportUrl;
const clientUrl = window._page.currentView?.clientUrl;
const loginForm = useTemplateRef('login-form');

const onSubmit = () => {
  loginForm?.value?.submit();
};

const usernameError = computed(() => {
  return firstError ? '' : null;
});
const passwordError = computed(() => {
  return firstError ? '' : null;
});

// CheckboxInput requires a valid ref as a model to show the check icon
const rememberMeChecked = ref(rememberMe);
</script>

<script>
export default {
  name: 'LoginView'
};
</script>

<template>
  <notice-bar :type="NoticeBarTypes.Critical" v-if="firstError">{{ firstError }}</notice-bar>
  <message-bar v-else/>

  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>

  <h2 data-testid="header-text">{{ $t('loginAccountTitle') }}</h2>
  <form id="kc-form-login" ref="login-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
        @keyup.enter="onSubmit">
    <div class="form-elements">
      <text-input
        data-testid="username-input"
        id="username"
        name="username"
        required
        autocomplete="username webauthn"
        autofocus
        :error="usernameError"
        outerSuffix="@thundermail.com"
      >
        {{ $t('email') }}
      </text-input>
      <text-input
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

    <a
      v-if="forgotPasswordUrl"
      :href="forgotPasswordUrl"
      class="forgot-password-link"
    >
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
    <template v-if="registerUrl">
      <i18n-t keypath="goToRegister" tag="span">
        <a :href="registerUrl" data-testid="go-to-register-url">{{ $t('goToRegisterAction') }}</a>
      </i18n-t>

      •
    </template>
    <i18n-t keypath="needHelp" tag="span">
      <a :href="supportUrl" data-testid="go-to-support-url">{{ $t('needHelpAction') }}</a>
    </i18n-t>
  </div>
</template>

<style scoped>
.notice-bar {
  position: absolute;
  top: 1rem;
  left: 1.5rem;
  right: 1.5rem;
  z-index: 1;
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
  display: block;
  font-size: 0.6875rem;
  color: var(--colour-ti-muted);
  margin-block-end: 2rem;
}

.footer-link-container {
  display: flex;
  gap: 0.425rem;
  flex-wrap: wrap;
  justify-content: center;
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
