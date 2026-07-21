<script setup>
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import { submitKeycloakForm } from '@kc/vue/keycloakForm';
const formAction = window._page.currentView?.formAction;
const logoutForm = useTemplateRef('logout-form');

const sessionCode = window._page.currentView?.sessionCode;
const clientUrl = window._page.currentView?.clientUrl;
const onSubmit = () => {
  submitKeycloakForm(logoutForm?.value);
};
</script>

<script>
export default {
  name: 'LogoutView'
};
</script>

<template>
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
