<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhArrowSquareOut, PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';

import ActionCard from '@/components/ActionCard.vue';

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
        <a href="https://www.thunderbird.net/thunderbird/all/" target="_blank" rel="noopener noreferrer" class="download-link">
          <primary-button size="small" variant="outline">
            {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadButton') }}
          </primary-button>
        </a>
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

.download-link {
  display: inline-block;
  text-decoration: none;
}
</style>
