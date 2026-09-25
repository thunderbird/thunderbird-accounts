<script setup lang="ts">
import { useI18n } from 'vue-i18n';

// Shared components
import CardContainer from '@/components/CardContainer.vue';

// Local components
import AccountActivity from './components/AccountActivity.vue';
import ConnectedApps from './components/ConnectedApps.vue';
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
      <account-activity class="security-section" />
      <connected-apps class="security-section" />
      <allow-list v-if="false" class="security-section" />
    </card-container>
  </div>
</template>

<style scoped>
.security-settings-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;

  .security-settings-card {
    width: 100%;
  }

  .security-section:not(:last-child) {
    margin-block-end: 2.25rem;
  }
}
</style>
