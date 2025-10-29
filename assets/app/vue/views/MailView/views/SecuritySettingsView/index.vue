<script setup lang="ts">
import { useI18n } from 'vue-i18n';

// Shared components
import CardContainer from '@/components/CardContainer.vue';

// Local components
import AccountActivity from './components/AccountActivity.vue';
import AllowList from './components/AllowList.vue';

const { t } = useI18n();
</script>

<script lang="ts">
export default {
  name: 'SecuritySettingsView',
};
</script>

<template>
  <div class="security-settings-view">
    <card-container class="security-settings-card">
      <h2>{{ t('views.mail.views.securitySettings.securitySettings') }}</h2>

      <account-activity />
      <allow-list />
    </card-container>
  </div>
</template>

<style scoped>
.security-settings-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;

  .security-settings-card {
    display: flex;
    flex-direction: column;
    gap: 2.25rem;
    width: 100%;

    h2 {
      font-size: 1.5rem;
      font-weight: 500;
      font-family: metropolis;
      color: var(--colour-ti-highlight);
    }
  }
}

@media (min-width: 1024px) {
  .security-settings-view {
    .security-settings-card {
      width: 971px;
      margin: 0 auto;
    }
  }
}
</style>
