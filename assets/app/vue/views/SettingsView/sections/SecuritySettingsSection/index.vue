<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDevices } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';

const { t } = useI18n();
const showSecuritySettings = computed(() => isWaffleFlagActive(WAFFLE_FLAG.ACTIVE_LOGINS));
</script>

<script lang="ts">
export default {
  name: 'SecuritySettingsSection',
};
</script>

<template>
  <card-container v-if="showSecuritySettings" :title="t('views.mail.views.securitySettings.securitySettings')">
    <details-summary :title="t('views.settings.accountAccess')" :expandable="false" default-open>
      <template #icon>
        <ph-devices size="24" aria-hidden="true" />
      </template>

      <div class="account-access">
        <p>{{ t('views.settings.accountAccessDescription') }}</p>

        <router-link v-slot="{ href, navigate }" custom to="/settings/security">
          <primary-button :href="href" variant="outline" @click="navigate">
            {{ t('views.settings.manageAccountAccess') }}
          </primary-button>
        </router-link>
      </div>
    </details-summary>
  </card-container>
</template>

<style scoped>
.account-access {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1.5rem;
  color: var(--colour-ti-secondary);
  line-height: 1.32;
}
</style>
