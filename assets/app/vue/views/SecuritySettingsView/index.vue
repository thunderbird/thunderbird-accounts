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
      <div class="security-sections">
        <account-activity />
        <connected-apps />
        <allow-list v-if="false" />
      </div>
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

  .security-sections {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }
}
</style>
