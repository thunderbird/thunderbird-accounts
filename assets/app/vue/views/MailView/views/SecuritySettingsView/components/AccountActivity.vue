<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDevices } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import { LinkButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import SecurityAccessTable from './SecurityAccessTable.vue';

// API
import { getActiveSessions, signOutSession } from '../api';

// Types
import type { ActiveSession } from '../types';

// Utils
import { formatDate, formatDeviceInfo, formatSessionLocation } from '../formatters';

const { t, locale } = useI18n();

type DisplaySession = {
  id: string;
  label: string;
  ipAddress: string;
  isCurrent: boolean;
  location: string;
  lastAccess: string;
};

const isRenderableSession = (session: ActiveSession) => (
  Boolean(session.id)
  && Boolean(session.ip_address)
  && Number.isFinite(session.last_access)
);

const activeSessions = ref<DisplaySession[]>([]);
const loading = ref(true);
const errorMessage = ref(null);

const signOut = async (id: string) => {
  if (window.confirm(t('views.mail.views.securitySettings.signOutConfirmation'))) {
    try {
      await signOutSession(id);
      activeSessions.value = activeSessions.value.filter((session) => session.id !== id);
    } catch (error) {
      console.log(error);
      errorMessage.value = t('views.mail.views.securitySettings.errorSigningOutSession');
    }
  }
};

onMounted(async () => {
  try {
    const data = await getActiveSessions();

    const sortedData = data
      .filter(isRenderableSession)
      .sort((a: ActiveSession, b: ActiveSession) => b.last_access - a.last_access);

    activeSessions.value = sortedData.map((session: ActiveSession) => ({
      id: session.id,
      label: formatDeviceInfo(session.device_info, t('views.mail.views.securitySettings.unknownDevice')),
      ipAddress: session.ip_address,
      isCurrent: Boolean(session.is_current),
      location: formatSessionLocation(session.location, locale.value, t('views.mail.views.securitySettings.unknownLocation')),
      lastAccess: formatDate(new Date(session.last_access), locale.value, t),
    }));
  } catch (error) {
    console.log(error);
    errorMessage.value = t('views.mail.views.securitySettings.errorLoadingActiveSessions');
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <details-summary
    id="current-sign-ins"
    :title="t('views.mail.views.securitySettings.accountActivity')"
    :expandable="false"
    default-open
  >
    <template #icon>
      <ph-devices size="24" />
    </template>

    <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">
      <p>{{ errorMessage }}</p>
    </notice-bar>

    <template v-if="loading">
      <p class="account-activity-description">{{ t('views.mail.views.securitySettings.loadingActiveSessions') }}</p>
    </template>

    <template v-else-if="activeSessions.length > 0">
      <p class="account-activity-description">{{ t('views.mail.views.securitySettings.accountActivityDescription') }}</p>
  
      <security-access-table
        :records="activeSessions"
        :column-labels="{
          primary: t('views.mail.views.securitySettings.recordsTableHeaderDevice'),
          ipAddress: t('views.mail.views.securitySettings.recordsTableHeaderIpAddress'),
          location: t('views.mail.views.securitySettings.recordsTableHeaderLocation'),
          lastAccess: t('views.mail.views.securitySettings.recordsTableHeaderLastActive'),
          actions: t('views.mail.views.securitySettings.recordsTableHeaderActions'),
        }"
        :attribution="t('views.mail.views.securitySettings.ipGeolocationAttribution')"
      >
        <template #action="{ record }">
          <span v-if="record.isCurrent" class="current-session-label">
            {{ t('views.mail.views.securitySettings.thisIsYou') }}
          </span>
          <link-button v-else @click="signOut(record.id)">
            {{ t('views.mail.views.securitySettings.signOut') }}
          </link-button>
        </template>
      </security-access-table>
    </template>
    <template v-else>
      <p class="account-activity-description empty">{{ t('views.mail.views.securitySettings.noRecentDevices') }}</p>
    </template>
  </details-summary>
</template>

<style scoped>
.notice-bar {
  margin-block-end: 1rem;
}

.account-activity-description {
  color: var(--colour-ti-secondary);
  line-height: 1.32;
  margin-block-end: 1rem;

  &.empty {
    margin-block-end: 0;
  }
}

.current-session-label {
  color: var(--colour-ti-muted);
  font-size: 0.75rem;
}
</style>
