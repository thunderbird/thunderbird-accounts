<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhSliders } from '@phosphor-icons/vue';

// Shared components
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

// Local components
import AppPasswordSide from './components/AppPasswordSide.vue';
import UserInfoSide from './components/UserInfoSide.vue';
import EmailAliases from './components/EmailAliases.vue';
import ViewServerSettings from './components/ViewServerSettings.vue';

const { t } = useI18n();

const appPasswords = ref<string[]>(window._page?.appPasswords || []);
</script>

<script lang="ts">
export default {
  name: 'EmailSettingsSection',
};
</script>

<template>
  <section id="email-settings">
    <card-container :title="t('views.mail.sections.emailSettings.emailSettings')">
      <div class="email-settings-content">
        <user-info-side/>
        <app-password-side :app-passwords="appPasswords" />
      </div>

      <details-summary
        class="email-aliases-details-summary"
        :title="t('views.mail.sections.emailSettings.emailAliases')"
        default-open
      >
        <template #icon>
          <ph-sliders size="24" />
        </template>

        <email-aliases />
      </details-summary>

      <view-server-settings />
    </card-container>
  </section>
</template>

<style scoped>
.email-settings-content {
  display: grid;
  grid-template-columns: 1fr;
  column-gap: 2rem;
  margin-block-end: 2.25rem;
  color: var(--colour-ti-secondary);
}

.email-aliases-details-summary {
  position: relative;
  margin-block-end: 2.25rem;
}

@media (min-width: 768px) {
  .email-settings-content {
    grid-template-columns: 1fr 1fr;
  }
}

@media (min-width: 1280px) {
  .email-aliases-details-summary :deep(.tour-card) {
    right: -1.5rem;
  }
}
</style>
