<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhPlugsConnected } from '@phosphor-icons/vue';
import { DangerButton, LinkButton, ModalDialog, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import DetailsSummary from '@/components/DetailsSummary.vue';
import SecurityAccessTable from './SecurityAccessTable.vue';

import { getConnectedApps, revokeConnectedApp } from '../api';
import type { ConnectedApp, DisplayConnectedApp } from '../types';
import { formatDate, formatSessionLocation } from '../formatters';

const { t, locale } = useI18n();

const connectedAppsData = ref<ConnectedApp[]>([]);
const connectedApps = computed<DisplayConnectedApp[]>(() =>
  [...connectedAppsData.value]
    .sort((a, b) => (b.last_access || 0) - (a.last_access || 0))
    .map((app) => ({
      id: `${app.client_id}:${app.session_id ?? 'offline'}`,
      clientId: app.client_id,
      label: app.app_name || t('views.mail.views.securitySettings.unknownApp'),
      ipAddress: app.ip_address || t('views.mail.views.securitySettings.unknownIpAddress'),
      location: formatSessionLocation(
        app.location,
        locale.value,
        t('views.mail.views.securitySettings.unknownLocation')
      ),
      accessGiven:
        typeof app.access_given === 'number' && Number.isFinite(app.access_given)
          ? formatDate(new Date(app.access_given), locale.value, t)
          : t('views.mail.views.securitySettings.unknownAccessGiven'),
      lastAccess:
        typeof app.last_access === 'number' && Number.isFinite(app.last_access)
          ? formatDate(new Date(app.last_access), locale.value, t)
          : t('views.mail.views.securitySettings.unknownLastAccess'),
    }))
);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const appPendingRemoval = ref<DisplayConnectedApp | null>(null);
const removeAccessModal = useTemplateRef<InstanceType<typeof ModalDialog>>('removeAccessModal');

const confirmRemoveAccess = (id: string) => {
  const app = connectedApps.value.find((connectedApp) => connectedApp.id === id);
  if (!app) {
    return;
  }

  appPendingRemoval.value = app;
  removeAccessModal.value?.show();
};

const removeAccess = async () => {
  const app = appPendingRemoval.value;
  if (!app) {
    return;
  }

  removeAccessModal.value?.hide();

  try {
    await revokeConnectedApp(app.clientId);
    connectedAppsData.value = connectedAppsData.value.filter((connectedApp) => connectedApp.client_id !== app.clientId);
  } catch (error) {
    console.log(error);
    errorMessage.value = t('views.mail.views.securitySettings.errorRemovingAccess');
  }
};

onMounted(async () => {
  try {
    connectedAppsData.value = await getConnectedApps();
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
          accessGiven: t('views.mail.views.securitySettings.recordsTableHeaderAccessGiven'),
          lastAccess: t('views.mail.views.securitySettings.recordsTableHeaderLastAccess'),
          actions: t('views.mail.views.securitySettings.recordsTableHeaderActions'),
        }"
      >
        <template #action="{ record }">
          <link-button @click="confirmRemoveAccess(record.id)">
            {{ t('views.mail.views.securitySettings.removeAccess') }}
          </link-button>
        </template>
      </security-access-table>
    </template>

    <template v-else>
      <p class="connected-apps-description empty">{{ t('views.mail.views.securitySettings.noConnectedApps') }}</p>
    </template>
  </details-summary>

  <modal-dialog ref="removeAccessModal" @closed="appPendingRemoval = null">
    <template #header>
      <h2 id="title">
        {{
          t('views.mail.views.securitySettings.removeAccessConfirmation', {
            app: appPendingRemoval?.label,
          })
        }}
      </h2>
    </template>

    <p>{{ t('views.mail.views.securitySettings.removeAccessConfirmationDescription') }}</p>

    <template #actions>
      <link-button @click="removeAccessModal?.hide()">
        {{ t('views.mail.views.securitySettings.cancel') }}
      </link-button>
      <danger-button @click="removeAccess">
        {{ t('views.mail.views.securitySettings.removeAccess') }}
      </danger-button>
    </template>
  </modal-dialog>
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
