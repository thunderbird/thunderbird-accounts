<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDevices } from '@phosphor-icons/vue';
import { NoticeBar, NoticeBarTypes, PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';
import { getActiveSessions, getConnectedApps } from '@/views/MailView/views/SecuritySettingsView/api';
import EmailSettingsSection from '@/views/MailView/sections/EmailSettingsSection/index.vue';

defineOptions({ name: 'SettingsView' });

const { t } = useI18n();
const loading = ref(true);
const sessionCount = ref<number | null>(null);
const appCount = ref<number | null>(null);

const showSecuritySettings = computed(() => isWaffleFlagActive(WAFFLE_FLAG.ACTIVE_LOGINS));

onMounted(async () => {
  if (!showSecuritySettings.value) {
    return;
  }

  const [sessions, apps] = await Promise.allSettled([getActiveSessions(), getConnectedApps()]);
  if (sessions.status === 'fulfilled') {
    sessionCount.value = sessions.value.length;
  }
  if (apps.status === 'fulfilled') {
    appCount.value = apps.value.length;
  }
  loading.value = false;
});
</script>

<template>
  <div class="settings-view">
    <email-settings-section />

    <card-container v-if="showSecuritySettings" :title="t('views.mail.views.securitySettings.securitySettings')">
      <details-summary :title="t('views.settings.accountAccess')" :expandable="false" default-open>
        <template #icon>
          <ph-devices size="24" aria-hidden="true" />
        </template>

        <div class="account-access">
          <p>{{ t('views.settings.accountAccessDescription') }}</p>

          <notice-bar v-if="!loading && sessionCount === null" :type="NoticeBarTypes.Critical">
            <p>{{ t('views.mail.views.securitySettings.errorLoadingActiveSessions') }}</p>
          </notice-bar>
          <notice-bar v-if="!loading && appCount === null" :type="NoticeBarTypes.Critical">
            <p>{{ t('views.mail.views.securitySettings.errorLoadingConnectedApps') }}</p>
          </notice-bar>

          <dl class="access-counts" aria-live="polite" :aria-busy="loading">
            <dt>{{ t('views.mail.views.securitySettings.accountActivity') }}</dt>
            <dd>{{ loading ? t('views.settings.loading') : sessionCount ?? t('views.settings.unavailable') }}</dd>
            <dt>{{ t('views.mail.views.securitySettings.connectedApps') }}</dt>
            <dd>{{ loading ? t('views.settings.loading') : appCount ?? t('views.settings.unavailable') }}</dd>
          </dl>

          <router-link v-slot="{ href, navigate }" custom to="/settings/security">
            <primary-button :href="href" variant="outline" @click="navigate">
              {{ t('views.settings.manageAccountAccess') }}
            </primary-button>
          </router-link>
        </div>
      </details-summary>
    </card-container>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.account-access {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1.5rem;
  color: var(--colour-ti-secondary);
  line-height: 1.32;
}

.access-counts {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2rem;
  width: 100%;
  padding: 1rem;
  border-radius: var(--border-radius);
  background-color: var(--colour-neutral-lower);
  font-size: var(--txt-default);

  dt {
    font-weight: 700;
  }

  dd {
    overflow-wrap: anywhere;
  }
}
</style>
