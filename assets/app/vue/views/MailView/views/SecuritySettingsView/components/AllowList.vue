<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhShieldCheck } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

const { t } = useI18n();
</script>

<template>
  <details-summary :title="t('views.mail.views.securitySettings.allowList')" :expandable="false" default-open>
    <template #icon>
      <ph-shield-check size="24" />
    </template>
  </details-summary>
</template>

<style scoped>
</style>