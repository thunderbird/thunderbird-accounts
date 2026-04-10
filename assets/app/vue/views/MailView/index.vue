<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTour, FTUE_STEPS } from '@/composables/useTour';
import { LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';
import { PhXCircle } from '@phosphor-icons/vue';

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
    <div class="header-card" v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.INITIAL">
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
    <div class="header-card final" v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.FINAL">
      <header>
        <p class="step-label">{{ t('views.mail.ftue.step', { step: tour.currentStep.value, total: FTUE_STEPS.FINAL }) }}</p>
        <button class="close-button" @click="tour.skip()">
          <ph-x-circle size="24" />
        </button>
      </header>

      <div class="content">
        <p>{{ t('views.mail.ftue.step5Text') }}</p>
  
        <div class="buttons-container">
          <link-button size="small" @click="tour.back()">
            {{ t('views.mail.ftue.back') }}
          </link-button>
          <primary-button size="small" @click="tour.next()">
            {{ t('views.mail.ftue.done') }}
          </primary-button>
        </div>
      </div>
    </div>
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

  &.final {
    gap: 0.5rem;
  }

  h2 {
    font-weight: 700;
    font-size: 0.875rem;
    margin: 0;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .step-label {
      font-size: 0.6875rem;
    }
  }

  .content {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .close-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    color: var(--colour-ti-muted);
  }

  .buttons-container {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
}
</style>
