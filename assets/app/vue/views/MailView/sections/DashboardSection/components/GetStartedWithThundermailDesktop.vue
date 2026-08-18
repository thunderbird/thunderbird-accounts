<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { onClickOutside, onKeyStroke } from '@vueuse/core';
import { PhArrowSquareOut, PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton, ToolTip } from '@thunderbirdops/services-ui';
import ActionCard from '@/components/ActionCard.vue';
import { DOWNLOAD_THUNDERBIRD_DESKTOP_URL } from '@/defines';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';

const { t } = useI18n();
const isConnecting = ref(false);
const error = ref<string | null>(null);
const isTooltipVisible = ref(false);

const connectAction = useTemplateRef('connectAction');

onClickOutside(connectAction, () => {
  isTooltipVisible.value = false;
});

onKeyStroke('Escape', () => {
  isTooltipVisible.value = false;
});

// From Stalwart, primary email is always the first email address in the list
const primaryEmail = window._page?.emailAddresses?.[0] || '';
const userDisplayName = window._page?.userDisplayName || primaryEmail;
const showConnectNow = isWaffleFlagActive(WAFFLE_FLAG.SHOW_CONNECT_NOW);

async function handleConnectClick() {
  isConnecting.value = true;
  error.value = null;
  isTooltipVisible.value = true;

  try {
    // The API on TB Desktop side requires a token to be passed
    // to trigger Account Hub. However, TB Desktop will open the external browser
    // and get the actual refresh token by itself since we are already logged in at this point.
    const url =
      'net.thunderbird://thundermail/add' +
      `?name=${encodeURIComponent(userDisplayName)}` +
      `&email=${encodeURIComponent(primaryEmail)}` +
      `&token=not-a-real-token`;

    window.location.href = url;
  } catch (_error) {
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
    <template v-if="showConnectNow">
      <action-card
        :title="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectTitle')"
        :description="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectDescription')"
      >
        <p class="error-message" v-if="error">{{ error }}</p>

        <template #icon>
          <ph-arrow-square-out :size="20" />
        </template>
        <template #action>
          <div class="connect-action" ref="connectAction">
            <primary-button
              size="small"
              :disabled="isConnecting"
              :aria-expanded="isTooltipVisible"
              aria-controls="connect-now-tooltip"
              @click="handleConnectClick"
              class="button-link"
            >
              {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButton') }}
            </primary-button>
            <tool-tip
              v-if="isTooltipVisible"
              id="connect-now-tooltip"
              role="status"
              :alt="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButtonTooltip')"
            >
              <i18n-t keypath="views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButtonTooltip" tag="p">
                <template #downloadLink>
                  <a :href="DOWNLOAD_THUNDERBIRD_DESKTOP_URL" target="_blank" rel="noopener noreferrer">
                    {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButtonTooltipDownloadLink') }}
                  </a>
                </template>
              </i18n-t>
            </tool-tip>
          </div>
        </template>
      </action-card>
    </template>
    <template v-else>
      <action-card
        :title="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.autoConfigTitle')"
        :description="t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.autoConfigDescription')"
      />
    </template>

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

.connect-action {
  position: relative;
  display: inline-flex;
}

.connect-action :deep(.tooltip) {
  top: auto;
  bottom: calc(100% + 1rem);
  left: 50%;
  transform: translateX(-50%);
  max-width: 17rem;

  p {
    font-size: 0.75rem;
  }

  a {
    color: var(--colour-ti-highlight);
  }
}

.error-message {
  font-size: 0.75rem;
  color: var(--colour-danger-default);
}
</style>
