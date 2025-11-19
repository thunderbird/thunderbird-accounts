<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useTour, FTUE_STEPS } from '@/composables/useTour';
import { LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';

import DashboardSection from './sections/DashboardSection/index.vue';
import EmailSettingsSection from './sections/EmailSettingsSection/index.vue';
import CustomDomainsSection from './sections/CustomDomainsSection/index.vue';

// TODO: Uncomment when implementing security settings
// import SecuritySettingsSection from './sections/SecuritySettingsSection.vue';

const { t } = useI18n();
const tour = useTour();
</script>

<script lang="ts">
export default {
  name: 'MailView',
};
</script>

<template>
  <div class="mail-view">
    <dashboard-section />
    <email-settings-section />
    <custom-domains-section />

    <!-- TODO: Uncomment when implementing security settings -->
    <!-- <security-settings-section /> -->

    <!-- FTUE Initial Welcome Tour Card -->
    <div class="initial-welcome" v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.INITIAL">
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
  </div>
</template>

<style scoped>
.mail-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;

  section {
    width: 100%;
  }
}

/* Overriding the link button font size */
:deep(.base.link.small.filled > span) {
  font-size: 0.75rem;
}

.initial-welcome {
  position: absolute;
  top: 4.75rem;
  right: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 240px;
  padding: 0.75rem 1rem;
  color: var(--colour-ti-base);
  background-color: var(--colour-neutral-base);
  box-shadow: 0.25rem 0.25rem 1rem 0 rgba(0, 0, 0, 0.1);
  border-radius: 0.5rem;
  font-size: 0.875rem;

  h2 {
    font-weight: 700;
    font-size: 0.875rem;
  }

  .buttons-container {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
}

@media (min-width: 1024px) {
  .mail-view {
    section {
      width: 971px;
      margin: 0 auto;
    }
  }
}
</style>
