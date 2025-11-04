<script setup lang="ts">
import DashboardSection from './sections/DashboardSection/index.vue';
import EmailSettingsSection from './sections/EmailSettingsSection/index.vue';
import CustomDomainsSection from './sections/CustomDomainsSection/index.vue';

// TODO: Uncomment when implementing security settings
// import SecuritySettingsSection from './sections/SecuritySettingsSection.vue';
</script>

<script lang="ts">
export default {
  name: 'MailView',
};
</script>

<template>
  <div class="mail-view">
    <dashboard-section />
    <email-settings-section />
    <custom-domains-section />

    <!-- TODO: Uncomment when implementing security settings -->
    <!-- <security-settings-section /> -->
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
      width: 971px;
      margin: 0 auto;
    }
  }
}
</style>
