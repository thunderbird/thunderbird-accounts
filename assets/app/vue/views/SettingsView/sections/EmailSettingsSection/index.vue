<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';

// Shared components
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import EmailAliasesIcon from '@/components/icons/EmailAliasesIcon.vue';

// Local components
import EmailAliases from './components/EmailAliases.vue';
import ViewServerSettings from './components/ViewServerSettings.vue';
import CustomDomainsSection from './CustomDomainsSection/index.vue';

const { t } = useI18n();

const isCustomDomainsRevampActive = computed(() => isWaffleFlagActive(WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP));
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
          <email-aliases-icon />
        </template>

        <email-aliases />
      </details-summary>

      <custom-domains-section v-if="!isCustomDomainsRevampActive" />

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
