<script setup lang="ts">
import DashboardSection from './sections/DashboardSection/index.vue';
import ManageEmailsSection from './sections/ManageEmailsSection.vue';
import CustomDomainsSection from './sections/CustomDomainsSection.vue';
import SecuritySettingsSection from './sections/SecuritySettingsSection.vue';
</script>

<script lang="ts">
export default {
  name: 'MailView',
};
</script>

<template>
  <div class="mail-view">
    <dashboard-section />
    <manage-emails-section />
    <custom-domains-section />
    <security-settings-section />
  </div>
</template>

<style scoped>
.mail-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;

  section {
    width: 100%;
  }
}

@media (min-width: 1024px) {
  .mail-view {
    section {
      min-width: 971px;
    }
  }
}
</style>
