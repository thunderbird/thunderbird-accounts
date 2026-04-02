<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDesktop, PhDeviceMobile, PhGlobe } from '@phosphor-icons/vue';

import CardContainer from '@/components/CardContainer.vue';
import { SETUP_TABS, SegmentedControlTab } from '../types';
import SegmentedControlSlider from './SegmentedControlSlider.vue';
import GetStartedWithThundermailDesktop from './GetStartedWithThundermailDesktop.vue';
import GetStartedWithThundermailMobile from './GetStartedWithThundermailMobile.vue';
import GetStartedWithThundermailOtherApps from './GetStartedWithThundermailOtherApps.vue';

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

// https://vite.dev/guide/assets.html#new-url-url-import-meta-url
const thunderbirdClientImage = new URL('@/assets/png/thundermail-dashboard-client.png', import.meta.url).href;
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
    <div class="get-started-with-thundermail-content">
      <segmented-control-slider
        v-model="selectedTab"
        :tabs="tabs"
        :label="t('views.mail.sections.dashboard.getStartedWithThundermail.title')"
      >
        <template #desktop>
          <get-started-with-thundermail-desktop />
        </template>
  
        <template #mobile>
          <get-started-with-thundermail-mobile />
        </template>
  
        <template #other>
          <get-started-with-thundermail-other-apps />
        </template>
      </segmented-control-slider>

      <img class="thunderbird-client-image" :src="thunderbirdClientImage" :alt="t('views.mail.sections.dashboard.getStartedWithThundermail.imgAlt')" />
    </div>
  </card-container>
</template>

<style scoped>
.get-started-with-thundermail-content {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;

  .thunderbird-client-image {
    max-width: 306px;
    height: 100%;
    object-fit: contain;
  }
}
</style>