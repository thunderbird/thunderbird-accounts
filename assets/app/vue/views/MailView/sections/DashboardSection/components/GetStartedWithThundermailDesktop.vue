<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhArrowSquareOut, PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import ActionCard from '@/components/ActionCard.vue';
import { DOWNLOAD_THUNDERBIRD_DESKTOP_URL } from '@/defines';

const { t } = useI18n();

const showConnectNow = window.localStorage.getItem('feature.show-connect-now') === 'true';

// TODO: Update this when the full URL is ready
const tbDesktopCustomProtocolUrl = 'net.thunderbird://replay';
</script>

<script lang="ts">
export default {
  name: 'GetStartedWithThundermailDesktop',
};
</script>

<template>
  <div class="action-cards">
    <action-card
      v-if="showConnectNow"
      :title="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectTitle')"
      :description="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectDescription')"
    >
      <template #icon>
        <ph-arrow-square-out :size="20" />
      </template>
      <template #action>
        <primary-button
          size="small"
          :href="tbDesktopCustomProtocolUrl"
          class="button-link"
        >
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
          :variant="showConnectNow ? 'outline' : 'filled'"
          :href="DOWNLOAD_THUNDERBIRD_DESKTOP_URL"
          target="_blank"
          rel="noopener noreferrer"
          class="button-link"
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

.button-link {
  height: 2rem;
}
</style>
