<script setup lang="ts">
import { useI18n } from 'vue-i18n';

// Shared components
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import EmailAliasesIcon from '@/components/icons/EmailAliasesIcon.vue';

// Local components
import EmailAliases from './components/EmailAliases.vue';
import ViewServerSettings from './components/ViewServerSettings.vue';
import CustomDomainsSection from './CustomDomainsSection/index.vue';

const { t } = useI18n();
</script>

<script lang="ts">
export default {
  name: 'EmailSettingsSection',
};
</script>

<template>
  <section id="email-settings">
    <card-container :title="t('views.mail.sections.emailSettings.emailSettings')">
      <details-summary
        class="email-aliases-details-summary"
        :title="t('views.mail.sections.emailSettings.emailAliases')"
      >
        <template #icon>
          <email-aliases-icon aria-hidden="true" />
        </template>

        <email-aliases />
      </details-summary>

      <custom-domains-section />

      <view-server-settings />
    </card-container>
  </section>
</template>

<style scoped>
.email-aliases-details-summary {
  position: relative;
  margin-block-end: 2rem;
}
</style>
