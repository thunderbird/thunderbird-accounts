<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhHardDrives } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import ServerSettingsCard from '@/components/ServerSettingsCard.vue';

const { t } = useI18n();
</script>

<template>
  <details-summary :title="t('views.mail.sections.dashboard.viewServerSettings')" default-open>
    <template #icon>
      <ph-hard-drives size="24" />
    </template>

    <server-settings-card
      :is-manual-configuration-section="false"
      :show-footer="true"
    />
  </details-summary>
</template>
