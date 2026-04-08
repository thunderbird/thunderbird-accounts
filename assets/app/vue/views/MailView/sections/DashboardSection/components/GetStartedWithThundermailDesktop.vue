<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhArrowSquareOut, PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import ActionCard from '@/components/ActionCard.vue';
import { DOWNLOAD_THUNDERBIRD_DESKTOP_URL } from '@/defines';

const { t } = useI18n();

function onConnectNow() {
  // TODO: Implement connect action, custom protocol mapping TBD
}
</script>

<script lang="ts">
export default {
  name: 'GetStartedWithThundermailDesktop',
};
</script>

<template>
  <div class="action-cards">
    <action-card
      :title="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectTitle')"
      :description="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectDescription')"
    >
      <template #icon>
        <ph-arrow-square-out :size="20" />
      </template>
      <template #action>
        <primary-button size="small" @click="onConnectNow">
          {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButton') }}
        </primary-button>
      </template>
    </action-card>

    <action-card
      :title="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadTitle')"
      :description="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadDescription')"
    >
      <template #icon>
        <ph-download-simple :size="20" />
      </template>
      <template #action>
        <primary-button
          size="small"
          variant="outline"
          :href="DOWNLOAD_THUNDERBIRD_DESKTOP_URL"
          target="_blank"
          rel="noopener noreferrer"
          class="download-button"
        >
          {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadButton') }}
        </primary-button>
      </template>
    </action-card>
  </div>
</template>

<style scoped>
.action-cards {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.download-button {
  height: 2rem;
}
</style>
