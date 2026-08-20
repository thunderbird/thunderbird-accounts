<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhPlugsConnected } from '@phosphor-icons/vue';
import { LinkButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import DetailsSummary from '@/components/DetailsSummary.vue';
import SecurityAccessTable from './SecurityAccessTable.vue';

import { getConnectedApps, revokeConnectedApp } from '../api';
import type { ConnectedApp } from '../types';
import { formatDate, formatSessionLocation } from '../formatters';

const { t, locale } = useI18n();

type DisplayConnectedApp = {
  id: string;
  clientId: string;
  label: string;
  ipAddress: string;
  location: string;
  lastAccess: string;
};

const connectedApps = ref<DisplayConnectedApp[]>([]);
const loading = ref(true);
const errorMessage = ref<string | null>(null);

const removeAccess = async (id: string) => {
  const app = connectedApps.value.find((connectedApp) => connectedApp.id === id);
  if (!app) {
    return;
  }

  if (!window.confirm(t('views.mail.views.securitySettings.removeAccessConfirmation', { app: app.label }))) {
    return;
  }

  try {
    await revokeConnectedApp(app.clientId);
    connectedApps.value = connectedApps.value.filter((connectedApp) => connectedApp.clientId !== app.clientId);
  } catch (error) {
    console.log(error);
    errorMessage.value = t('views.mail.views.securitySettings.errorRemovingAccess');
  }
};

onMounted(async () => {
  try {
    const data = await getConnectedApps();
    const sortedData = [...data].sort((a, b) => (b.last_access || 0) - (a.last_access || 0));

    connectedApps.value = sortedData.map((app: ConnectedApp, index) => ({
      id: `${app.client_id}:${app.session_id || index}`,
      clientId: app.client_id,
      label: app.app_name || t('views.mail.views.securitySettings.unknownApp'),
      ipAddress: app.ip_address || t('views.mail.views.securitySettings.unknownIpAddress'),
      location: formatSessionLocation(
        app.location,
        locale.value,
        t('views.mail.views.securitySettings.unknownLocation')
      ),
      lastAccess:
        typeof app.last_access === 'number' && Number.isFinite(app.last_access)
          ? formatDate(new Date(app.last_access), locale.value, t)
          : t('views.mail.views.securitySettings.unknownLastAccess'),
    }));
  } catch (error) {
    console.log(error);
    errorMessage.value = t('views.mail.views.securitySettings.errorLoadingConnectedApps');
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <details-summary
    id="connected-apps"
    :title="t('views.mail.views.securitySettings.connectedApps')"
    :expandable="false"
    default-open
  >
    <template #icon>
      <ph-plugs-connected size="24" />
    </template>

    <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">
      <p>{{ errorMessage }}</p>
    </notice-bar>

    <template v-if="loading">
      <p class="connected-apps-description">{{ t('views.mail.views.securitySettings.loadingConnectedApps') }}</p>
    </template>

    <template v-else-if="connectedApps.length > 0">
      <p class="connected-apps-description">{{ t('views.mail.views.securitySettings.connectedAppsDescription') }}</p>

      <security-access-table
        :records="connectedApps"
        :column-labels="{
          primary: t('views.mail.views.securitySettings.recordsTableHeaderApp'),
          location: t('views.mail.views.securitySettings.recordsTableHeaderLocation'),
          lastAccess: t('views.mail.views.securitySettings.recordsTableHeaderLastAccess'),
          actions: t('views.mail.views.securitySettings.recordsTableHeaderActions'),
        }"
        :attribution="t('views.mail.views.securitySettings.ipGeolocationAttribution')"
      >
        <template #action="{ record }">
          <link-button @click="removeAccess(record.id)">
            {{ t('views.mail.views.securitySettings.removeAccess') }}
          </link-button>
        </template>
      </security-access-table>
    </template>

    <template v-else>
      <p class="connected-apps-description empty">{{ t('views.mail.views.securitySettings.noConnectedApps') }}</p>
    </template>
  </details-summary>
</template>

<style scoped>
.notice-bar {
  margin-block-end: 1rem;
}

.connected-apps-description {
  color: var(--colour-ti-secondary);
  line-height: 1.32;
  margin-block-end: 1rem;

  &.empty {
    margin-block-end: 0;
  }
}
</style>
