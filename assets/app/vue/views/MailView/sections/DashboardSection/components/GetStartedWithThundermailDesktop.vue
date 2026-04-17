<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhArrowSquareOut, PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import ActionCard from '@/components/ActionCard.vue';
import { DOWNLOAD_THUNDERBIRD_DESKTOP_URL } from '@/defines';
import { getDesktopConnectToken } from '../api';

const { t } = useI18n();
const isConnecting = ref(false);
const error = ref<string | null>(null);

// From Stalwart, primary email is always the first email address in the list
const primaryEmail = window._page?.emailAddresses?.[0] || '';
const userDisplayName = window._page?.userDisplayName || primaryEmail;
const showConnectNow = window.localStorage.getItem('feature.show-connect-now') === 'true';

async function handleConnectClick() {
  isConnecting.value = true;
  error.value = null;

  try {
    const data = await getDesktopConnectToken();

    if (!data.success) {
      error.value = t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.failedToGenerateToken');
      return;
    }

    const url =
      'net.thunderbird://add-thundermail/' +
      `?name=${encodeURIComponent(userDisplayName)}` +
      `&email=${encodeURIComponent(primaryEmail)}` +
      `&token=${encodeURIComponent(data.token)}`;

    window.location.href = url;
  } catch (error) {
    error.value = t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.desktopConnectionFailed');
  } finally {
    isConnecting.value = false;
  }
};
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
          :disabled="isConnecting"
          @click="handleConnectClick"
        >
          {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButton') }}
        </primary-button>
      </template>

      <p class="error-message" v-if="error">{{ error }}</p>
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

.error-message {
  font-size: 0.75rem;
  color: var(--colour-danger-default);
}
</style>
