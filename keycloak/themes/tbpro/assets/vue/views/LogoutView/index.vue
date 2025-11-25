<script setup>
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import MessageBar from '@kc/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@kc/svg/thunderbird-pro-light.svg';

const formAction = window._page.currentView?.formAction;
const logoutForm = useTemplateRef('logout-form');

const sessionCode = window._page.currentView?.sessionCode;
const clientUrl = window._page.currentView?.clientUrl;
const onSubmit = () => {
  logoutForm?.value?.submit();
};
</script>

<script>
export default {
  name: 'LogoutView'
};
</script>

<template>
  <message-bar />

  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>

  <h2>{{ $t('logoutConfirmTitle') }}</h2>
  <form id="kc-logout-confirm" ref="logout-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
        @keyup.enter="onSubmit">
    <p>{{ $t('logoutConfirmHeader') }}</p>
    <div class="buttons">
      <input type="hidden" name="session_code" :value="sessionCode">

      <primary-button data-testid="submit-btn" name="confirmLogout" id="kc-logout" class="submit" @click="onSubmit">
        {{ $t('doLogout') }}
      </primary-button>

      <template v-if="clientUrl">
        <a :href="clientUrl">{{ $t('backToApplication') }}</a>
      </template>
    </div>
  </form>
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

.buttons {
  display: flex;
  flex-direction: column;
  align-items: flex-start;;
  gap: 1rem;
  margin-top: var(--space-24);
  margin-bottom: var(--space-24);
  width: 100%;
}
</style>
