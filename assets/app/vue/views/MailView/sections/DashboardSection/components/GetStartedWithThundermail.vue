<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDesktop, PhDeviceMobile, PhGlobe, PhArrowSquareOut, PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';

import CardContainer from '@/components/CardContainer.vue';

import { SETUP_TABS } from '../types';
import type { SegmentedControlTab } from '../types';
import SegmentedControlSlider from './SegmentedControlSlider.vue';

const { t } = useI18n();
const selectedTab = ref<string>(SETUP_TABS.DESKTOP);

const tabs = computed<SegmentedControlTab[]>(() => [
  {
    id: SETUP_TABS.DESKTOP,
    label: t('views.mail.sections.dashboard.getStartedWithThundermail.tabs.desktop'),
    icon: PhDesktop,
  },
  {
    id: SETUP_TABS.MOBILE,
    label: t('views.mail.sections.dashboard.getStartedWithThundermail.tabs.mobile'),
    icon: PhDeviceMobile,
  },
  {
    id: SETUP_TABS.OTHER,
    label: t('views.mail.sections.dashboard.getStartedWithThundermail.tabs.otherApps'),
    icon: PhGlobe,
  },
]);

function onDesktopPanelConnectNow() {
  // TODO: Implement connect action, custom protocol mapping TBD
}
</script>

<script lang="ts">
export default {
  name: 'GetStartedWithThundermail',
};
</script>

<template>
  <card-container
    :title="t('views.mail.sections.dashboard.getStartedWithThundermail.title')"
    :subtitle="t('views.mail.sections.dashboard.getStartedWithThundermail.description')"
  >
    <segmented-control-slider
      v-model="selectedTab"
      :tabs="tabs"
      :label="t('views.mail.sections.dashboard.getStartedWithThundermail.title')"
    >
      <template #desktop>
        <div class="action-cards">
          <div class="action-card">
            <div class="action-content">
              <div class="action-header">
                <ph-arrow-square-out :size="20" />
                <p class="action-title">{{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectTitle') }}</p>
              </div>
              <p class="action-description">{{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectDescription') }}</p>
            </div>
            <primary-button size="small" @click="onDesktopPanelConnectNow">
              {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.connectButton') }}
            </primary-button>
          </div>

          <div class="action-card">
            <div class="action-content">
              <div class="action-header">
                <ph-download-simple :size="20" />
                <p class="action-title">{{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadTitle') }}</p>
              </div>
              <p class="action-description">{{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadDescription') }}</p>
            </div>
            <a href="https://www.thunderbird.net/thunderbird/all/" target="_blank" rel="noopener noreferrer" class="download-link">
              <primary-button size="small" variant="outline">
                {{ t('views.mail.sections.dashboard.getStartedWithThundermail.desktopPanel.downloadButton') }}
              </primary-button>
            </a>
          </div>
        </div>
      </template>

      <template #mobile>
        <!-- Mobile panel content -->
      </template>
      <template #other>
        <!-- Other Apps panel content -->
      </template>
    </segmented-control-slider>
  </card-container>
</template>

<style scoped>
.action-cards {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem 0.5rem 0.5rem;
  border: 1px solid var(--colour-neutral-border);
  border-radius: 8px;
  overflow: clip;
}

.action-content {
  display: flex;
  flex-direction: column;
  flex: 1 0 0;
  gap: 0.5rem;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--colour-ti-base);

  svg {
    color: var(--colour-ti-highlight);
  }
}

.action-title {
  flex: 1 0 0;
  font-family: Inter, sans-serif;
  font-size: 0.875rem;
  line-height: 1.23;
  color: var(--colour-ti-base);
}

.action-description {
  font-family: Inter, sans-serif;
  font-size: 0.75rem;
  line-height: normal;
  color: var(--colour-ti-secondary);
}

.download-link {
  display: inline-block;
  text-decoration: none;
}
</style>
