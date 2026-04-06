<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhSliders } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import ServerSettingsCard from '@/components/ServerSettingsCard.vue';

const { t } = useI18n();
</script>

<template>
  <details-summary :title="t('views.mail.sections.dashboard.viewServerSettings')">
    <template #icon>
      <ph-sliders size="24" />
    </template>

    <server-settings-card />
  </details-summary>
</template>
