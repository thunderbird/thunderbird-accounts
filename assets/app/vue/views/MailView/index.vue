<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTour, FTUE_STEPS } from '@/composables/useTour';
import TourCard from '@/components/TourCard.vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';

import EmailSettingsSection from './sections/EmailSettingsSection/index.vue';
import CustomDomainsSection from './sections/CustomDomainsSection/index.vue';

// TODO: Uncomment when implementing security settings
// import SecuritySettingsSection from './sections/SecuritySettingsSection.vue';

const { t } = useI18n();
const tour = useTour();
const webmailUrl = window._page?.webmailUrl;

const isCustomDomainsRevampActive = computed(() => isWaffleFlagActive(WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP));
</script>

<script lang="ts">
export default {
  name: 'MailView',
};
</script>

<template>
  <div class="mail-view">
    <notice-bar :type="NoticeBarTypes.Info" class="webmail-notice">
      <i18n-t keypath="views.mail.webmailAlpha.notice">
        <template #checkItOut>
          <a :href="webmailUrl" target="_blank" rel="noopener noreferrer">
            {{ t('views.mail.webmailAlpha.checkItOut') }}
          </a>
        </template>
      </i18n-t>
    </notice-bar>

    <email-settings-section />
    <custom-domains-section v-if="!isCustomDomainsRevampActive" />

    <!-- TODO: Uncomment when implementing security settings -->
    <!-- <security-settings-section /> -->

    <div id="tour-target-header" />

    <Teleport
      v-if="tour.showFTUE.value && tour.currentStepConfig.value?.teleportTarget"
      :to="tour.currentStepConfig.value.teleportTarget"
      defer
    >
      <tour-card
        data-tour-card
        :title="tour.currentStepConfig.value.titleKey
          ? t(tour.currentStepConfig.value.titleKey)
          : undefined"
        :text="t(tour.currentStepConfig.value.textKey)"
        :subtitle="tour.currentStepConfig.value.subtitleNextStepKey
          ? t('views.mail.ftue.nextStep', { step: t(tour.currentStepConfig.value.subtitleNextStepKey) })
          : undefined"
        :current-step="tour.currentStep.value"
        :total-steps="FTUE_STEPS.FINAL"
        :show-back="tour.currentStepConfig.value.showBack"
        :variant="tour.currentStepConfig.value.variant"
        :next-label="tour.currentStepConfig.value.nextLabelKey
          ? t(tour.currentStepConfig.value.nextLabelKey)
          : undefined"
        @next="tour.next()"
        @back="tour.back()"
        @close="tour.skip()"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.mail-view {
  display: flex;
  flex-direction: column;
}

.mail-view :deep(:not(:first-child) section) {
  margin-block-end: 2rem;
}

.webmail-notice {
  max-width: 968px;
  width: 100%;
  margin: 0 auto 2rem;
}
</style>
