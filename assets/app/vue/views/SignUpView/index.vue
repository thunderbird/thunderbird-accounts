<script setup lang="ts">
// Import Keycloak theme's style
import '@kc/css/main.css';
import kcEn from '@/locales/en.kc.json';

// Import the BaseTemplate and RegisterView from Keycloak
import RegisterView from '@kc/vue/views/RegisterView/index.vue';
import BaseTemplate from '@kc/vue/BaseTemplate.vue';

// Import our i18n composable
import i18nInstance from '@/composables/i18n';

// Keycloak also uses window page variables, so set them up as it expects
window._page.currentView = {
  errors: [],
  formAction: '',
  clientUrl: '',
  currentLocale: 'en',
};
window._page.pageId = 'sign-up';

// Merge some localization
i18nInstance.global.mergeLocaleMessage('en', { ...(kcEn ?? {}) });
</script>

<script lang="ts">
export default {
  name: 'SignUp',
};
</script>

<template>
  <base-template>
    <register-view />
  </base-template>
</template>

<style scoped></style>
