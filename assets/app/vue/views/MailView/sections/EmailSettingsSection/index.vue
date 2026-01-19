<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhSliders } from '@phosphor-icons/vue';
import { useTour, FTUE_STEPS } from '@/composables/useTour';

// Shared components
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import TourCard from '@/components/TourCard.vue';

// Local components
import AppPasswordSide from './components/AppPasswordSide.vue';
import UserInfoSide from './components/UserInfoSide.vue';
import EmailAliases from './components/EmailAliases.vue';

const { t } = useI18n();
const tour = useTour();

const appPasswords = window._page?.appPasswords || [];
</script>

<script lang="ts">
export default {
  name: 'EmailSettingsSection',
};
</script>

<template>
  <section id="email-settings">
    <card-container>
      <tour-card
        v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.FINAL"
        :text="t('views.mail.ftue.step3Text')"
        :next-label="t('views.mail.ftue.done')"
        :current-step="tour.currentStep.value"
        :total-steps="FTUE_STEPS.FINAL"
        show-back
        @next="tour.next()"
        @back="tour.back()"
        @close="tour.skip()"
      />

      <h2>{{ t('views.mail.sections.emailSettings.emailSettings') }}</h2>

      <div class="email-settings-content">
        <user-info-side/>
        <app-password-side :app-passwords="appPasswords" />
      </div>

      <details-summary :title="t('views.mail.sections.emailSettings.emailAliases')" default-open>
        <template #icon>
          <ph-sliders size="24" />
        </template>

        <email-aliases />
      </details-summary>
    </card-container>
  </section>
</template>

<style scoped>
h2 {
  font-size: 1.5rem;
  font-weight: 500;
  font-family: metropolis;
  color: var(--colour-ti-highlight);
  margin-block-end: 1.5rem;
}

.email-settings-content {
  display: grid;
  grid-template-columns: 1fr;
  column-gap: 2rem;
  margin-block-end: 2.25rem;
  color: var(--colour-ti-secondary);
}

@media (min-width: 768px) {
  .email-settings-content {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
