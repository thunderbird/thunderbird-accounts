<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTour, FTUE_STEPS } from '@/composables/useTour';
import { LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';
import TourCard from '@/components/TourCard.vue';

import WelcomeHeader from './sections/DashboardSection/components/WelcomeHeader.vue';
import GetStartedWithThundermail from './sections/DashboardSection/components/GetStartedWithThundermail.vue';
import EmailSettingsSection from './sections/EmailSettingsSection/index.vue';
import CustomDomainsSection from './sections/CustomDomainsSection/index.vue';

// TODO: Uncomment when implementing security settings
// import SecuritySettingsSection from './sections/SecuritySettingsSection.vue';

const { t } = useI18n();
const tour = useTour();
const isGetStartedPinned = ref(true);
</script>

<script lang="ts">
export default {
  name: 'MailView',
};
</script>

<template>
  <div class="mail-view">
    <section id="dashboard">
      <welcome-header />
      <div id="get-started-pinned-slot" class="teleport-target" />
    </section>

    <email-settings-section />
    <custom-domains-section />

    <div id="get-started-unpinned-slot" class="teleport-target" />

    <Teleport defer :to="isGetStartedPinned ? '#get-started-pinned-slot' : '#get-started-unpinned-slot'">
      <get-started-with-thundermail
        :is-pinned="isGetStartedPinned"
        @toggle-pinned="isGetStartedPinned = !isGetStartedPinned"
      />
    </Teleport>

    <!-- TODO: Uncomment when implementing security settings -->
    <!-- <security-settings-section /> -->

    <!-- FTUE Initial Welcome Tour Card -->
    <div
      data-tour-card
      class="header-card"
      v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.INITIAL"
      role="dialog"
      :aria-label="t('views.mail.ftue.initialWelcomeTitle')"
      aria-modal="false"
      tabindex="-1"
    >
      <h2>{{ t('views.mail.ftue.initialWelcomeTitle') }}</h2>
      <p>{{ t('views.mail.ftue.initialWelcomeDescription') }}</p>

      <div class="buttons-container">
        <link-button size="small" @click="tour.skip()">
          {{ t('views.mail.ftue.skip') }}
        </link-button>
        <primary-button size="small" @click="tour.next()">
          {{ t('views.mail.ftue.letsGo') }}
        </primary-button>
      </div>
    </div>

    <!-- FTUE Final Tour Card -->
    <tour-card
      data-tour-card
      v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.FINAL"
      variant="header"
      :text="t('views.mail.ftue.step5Text')"
      :current-step="tour.currentStep.value"
      :total-steps="FTUE_STEPS.FINAL"
      :next-label="t('views.mail.ftue.done')"
      show-back
      @next="tour.next()"
      @back="tour.back()"
      @close="tour.skip()"
    />
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

.teleport-target {
  display: contents;
}

/* Overriding the link button font size */
:deep(.base.link.small.filled > span) {
  font-size: 0.75rem;
}

.header-card {
  position: absolute;
  top: 4.75rem;
  right: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  width: 240px;
  padding: 0.75rem 1rem;
  color: var(--colour-ti-base);
  background-color: var(--colour-neutral-base);
  box-shadow: 0 0.5rem 1rem 0 rgba(0, 0, 0, 0.2);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  z-index: 10;

  h2 {
    font-weight: 700;
    font-size: 0.875rem;
    margin: 0;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }

  .buttons-container {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
}
</style>
