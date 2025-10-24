<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhSliders } from '@phosphor-icons/vue';

// Shared components
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

// Local components
import AppPasswordSide from './components/AppPasswordSide.vue';
import UserInfoSide from './components/UserInfoSide.vue';

const { t } = useI18n();

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
      <h2>{{ t('views.mail.sections.emailSettings.emailSettings') }}</h2>

      <div class="email-settings-content">
        <user-info-side :app-passwords="appPasswords" />
        <app-password-side :app-passwords="appPasswords" />
      </div>

      <details-summary :title="t('views.mail.sections.emailSettings.emailAliases')" default-open>
        <template #icon>
          <ph-sliders size="24" />
        </template>

        <div class="email-aliases-content">
          <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescription') }}</p>
          <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescriptionTwo', { aliasUsed: 3, aliasLimit: 10 }) }}</p>
        </div>
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

.email-aliases-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  line-height: 1.32;
  color: var(--colour-ti-secondary);

  & :last-child {
    font-style: italic;
    font-size: 0.75rem;
    color: var(--colour-ti-muted);
    line-height: normal;
  }
}

@media (min-width: 768px) {
  .email-settings-content {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
