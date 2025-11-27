<script setup>
import { TextInput, BrandButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { computed, ref, useTemplateRef } from 'vue';
import { PhArrowRight } from '@phosphor-icons/vue';
import MessageBar from '@kc/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@kc/svg/thunderbird-pro-light.svg';

const errors = window._page.currentView?.errors;
const formAction = window._page.currentView?.formAction;
const clientUrl = window._page.currentView?.clientUrl;
const tbProPrimaryDomain = `@${window._page.currentView?.tbProPrimaryDomain}`;

// Fixed values
const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
const locale = window._page.currentView?.currentLocale;

// Computed values
const username = ref();
const email = computed(() => {
  return `${username.value}@thundermail.com`;
});

const usernameError = computed(() => {
  return errors?.username === '' ? null : errors?.username;
});
const passwordError = computed(() => {
  return errors?.password === '' ? null : errors?.password;
});
const passwordConfirmError = computed(() => {
  return errors?.passwordConfirm === '' ? null : errors?.passwordConfirm;
});
const recoveryEmailError = computed(() => {
  return errors?.email === '' ? null : errors?.email;
});

const registerForm = useTemplateRef('register-form');

const onSubmit = () => {
  if (registerForm.value.checkValidity()) {
    registerForm?.value?.submit();
  }
};

</script>

<script>
export default {
  name: 'RegisterView'
};
</script>

<template>
  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>
  <h2>{{ $t('registerTitle') }}</h2>

  <slot name="notice-bars">
    <notice-bar :type="NoticeBarTypes.Critical" v-if="usernameError || passwordError || passwordConfirmError || recoveryEmailError">
      {{ $t('registerError') }}
    </notice-bar>
    <message-bar v-else/>
  </slot>

  <form id="kc-register-form" ref="register-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
        @keyup.enter="onSubmit">
    <div class="form-elements">
      <text-input
        data-testid="username-input"
        id="partialUsername"
        name="partialUsername"
        required
        autocomplete="username" 
        :error="usernameError"
        :outerSuffix="tbProPrimaryDomain"
        :help="$t('signUpUsernameHelp', {'domain': tbProPrimaryDomain})"
        v-model="username"
      >
        {{ $t('username') }}
      </text-input>
      <text-input
        data-testid="recovery-email-input"
        id="email"
        name="email"
        required
        autocomplete="email"
        :error="recoveryEmailError"
        :help="$t('recoveryEmailHelp')"
      >
        {{ $t('recoveryEmail') }}
      </text-input>
      <text-input
        data-testid="password-input"
        id="password"
        name="password"
        required
        autocomplete="new-password"
        type="password"
        :error="passwordError"
        :help="$t('signUpPasswordHelp')"
      >
        {{ $t('password') }}
      </text-input>
      <text-input
        data-testid="password-confirm-input"
        id="password-confirm"
        name="password-confirm"
        required
        autocomplete="confirm-password"
        type="password"
        :error="passwordConfirmError"
        :help="$t('signUpPasswordConfirmHelp')"
      >
        {{ $t('passwordConfirm') }}
      </text-input>
      <!-- These fields are dynamically filled out -->
      <text-input readonly data-testid="full-username-readonly-input" id="username" name="username" class="hidden" v-model="email"></text-input>
      <text-input readonly data-testid="locale-readonly-input" id="locale" name="locale" class="hidden" v-model="locale"></text-input>
      <text-input readonly data-testid="zoneinfo-readonly-input" id="zoneinfo" name="zoneinfo" class="hidden" v-model="timezone"></text-input>
      <slot name="form-extras"/>
    </div>
    <div class="buttons">
      <brand-button data-testid="submit" class="submit" @click="onSubmit">
        {{ $t('doRegister') }}

        <template #iconRight>
          <ph-arrow-right size="20" />
        </template>
      </brand-button>
    </div>
  </form>
</template>

<style scoped>
.hidden {
  display: none;
}

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
