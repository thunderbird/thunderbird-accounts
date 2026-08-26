<script setup>
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { ref, useTemplateRef } from 'vue';
const formAction = window._page.currentView?.formAction;
const logoutForm = useTemplateRef('logout-form');
// @submit and @keyup.enter can both fire for one Enter keypress; keep the POST single-shot (#1231).
const isSubmitting = ref(false);

const sessionCode = window._page.currentView?.sessionCode;
const clientUrl = window._page.currentView?.clientUrl;
const onSubmit = () => {
  if (isSubmitting.value) return;
  if (!logoutForm.value?.checkValidity()) return;
  isSubmitting.value = true;
  logoutForm.value.submit();
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

      <primary-button data-testid="submit-btn" name="confirmLogout" id="kc-logout" class="submit" @click="onSubmit"
                      :disabled="isSubmitting">
        {{ $t('doLogout') }}
      </primary-button>

      <template v-if="clientUrl">
        <a :href="clientUrl">{{ $t('backToApplication') }}</a>
      </template>
    </div>
  </form>
</template>

<style scoped>
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
