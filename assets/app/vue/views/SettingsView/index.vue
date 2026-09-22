<script setup lang="ts">
import EmailSettingsSection from './sections/EmailSettingsSection/index.vue';
import SecuritySettingsSection from './sections/SecuritySettingsSection/index.vue';

defineOptions({ name: 'SettingsView' });
</script>

<template>
  <div class="settings-view">
    <email-settings-section />
    <security-settings-section />
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
</style>
