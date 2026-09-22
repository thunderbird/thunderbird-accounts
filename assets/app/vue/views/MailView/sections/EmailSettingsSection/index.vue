<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';

// Shared components
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

// Local components
import EmailAliases from './components/EmailAliases.vue';
import ViewServerSettings from './components/ViewServerSettings.vue';
import CustomDomainsSection from '../CustomDomainsSection/index.vue';

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
          <svg class="email-aliases-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M8.667 4.524a8.737 8.737 0 0 0-6.129 2.5A8.464 8.464 0 0 0 0 13.055c0 2.262.913 4.432 2.538 6.032a8.737 8.737 0 0 0 6.129 2.499c1.792 0 3.675-.532 5.036-1.422a.661.661 0 0 0 .284-.417.646.646 0 0 0-.282-.674.672.672 0 0 0-.74-.002c-1.132.741-2.78 1.202-4.298 1.202a7.417 7.417 0 0 1-4.075-1.216 7.245 7.245 0 0 1-2.7-3.24 7.114 7.114 0 0 1-.418-4.17A7.185 7.185 0 0 1 3.481 7.95a7.37 7.37 0 0 1 3.755-1.975 7.441 7.441 0 0 1 4.237.41 7.31 7.31 0 0 1 3.291 2.66A7.139 7.139 0 0 1 16 13.055c0 2.17-.907 2.625-1.667 2.625s-1.666-.456-1.666-2.625V9.774a.651.651 0 0 0-.196-.464.672.672 0 0 0-.942 0 .651.651 0 0 0-.196.464v.35a4.056 4.056 0 0 0-4.465-.587 3.973 3.973 0 0 0-1.701 1.606 3.886 3.886 0 0 0 .409 4.416 4.005 4.005 0 0 0 1.968 1.277A4.06 4.06 0 0 0 9.9 16.8a4 4 0 0 0 1.928-1.336c.5.984 1.362 1.53 2.505 1.53 1.879 0 3-1.473 3-3.938a8.473 8.473 0 0 0-2.54-6.03 8.746 8.746 0 0 0-6.126-2.502Zm0 11.157a2.697 2.697 0 0 1-1.482-.443 2.635 2.635 0 0 1-.982-1.178 2.587 2.587 0 0 1-.152-1.516c.103-.51.357-.977.73-1.345a2.68 2.68 0 0 1 1.365-.718 2.706 2.706 0 0 1 1.541.15c.487.198.904.535 1.197.966a2.596 2.596 0 0 1-.332 3.315c-.5.492-1.178.769-1.885.769Z"
              fill="currentColor" />
            <path
              d="M22.889 6.556a.296.296 0 0 1-.296.296H19.63v2.963a.296.296 0 1 1-.593 0V6.852h-2.963a.296.296 0 0 1 0-.593h2.963V3.296a.296.296 0 1 1 .593 0V6.26h2.963a.297.297 0 0 1 .296.297Z"
              fill="currentColor" stroke="currentColor" stroke-width=".5" />
          </svg>
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

.email-aliases-icon {
  color: #37adf9; /* One-off colour, not in Bolt */
}
</style>
