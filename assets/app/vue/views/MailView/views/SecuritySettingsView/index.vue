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
    <card-container
      class="security-settings-card"
      :title="t('views.mail.views.securitySettings.securitySettings')"
    >
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
  }
}
</style>
