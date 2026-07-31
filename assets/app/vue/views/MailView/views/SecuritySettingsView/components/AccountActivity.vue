<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDevices } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import { LinkButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';

// API
import { getActiveSessions, signOutSession } from '../api';

// Types
import type { ActiveSession } from '../types';

// Utils
import { formatDate, formatDeviceInfo, formatSessionLocation } from '../formatters';

const { t, locale } = useI18n();

type DisplaySession = {
  id: string;
  deviceInfo: string;
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
      deviceInfo: formatDeviceInfo(session.device_info, t('views.mail.views.securitySettings.unknownDevice')),
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
  <details-summary :title="t('views.mail.views.securitySettings.accountActivity')" :expandable="false" default-open>
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
  
      <div class="records-table-wrapper" >
        <div class="records-table-header">
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderDevice') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderIpAddress') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderLocation') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderLastActive') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderActions') }}</p>
        </div>
  
        <div class="records-table-row" v-for="activeSession in activeSessions" :key="activeSession.id">
          <p>{{ activeSession.deviceInfo || t('views.mail.views.securitySettings.unknownDevice') }}</p>
          <p>{{ activeSession.ipAddress }}</p>
          <p>{{ activeSession.location }}</p>
          <p>{{ activeSession.lastAccess }}</p>
          <div class="sign-out-button-wrapper">
            <span v-if="activeSession.isCurrent" class="current-session-label">This is you</span>
            <link-button v-else @click="signOut(activeSession.id)">
              {{ t('views.mail.views.securitySettings.signOut') }}
            </link-button>
          </div>
        </div>
      </div>
      <p class="location-attribution">
        <a href="https://db-ip.com" rel="noopener noreferrer" target="_blank">
          {{ t('views.mail.views.securitySettings.ipGeolocationAttribution') }}
        </a>
      </p>
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

.records-table-wrapper {
  overflow-x: auto;
  margin-block-end: 1rem;
  color: var(--colour-ti-secondary);

  .records-table-header {
    height: 3rem;
    align-self: stretch;
    flex-grow: 0;
    display: flex;
    flex-direction: row;
    justify-content: flex-start;
    align-items: flex-start;
    padding: 0;
    border-block-end: solid 1px var(--surface-border-intense);
    min-width: max-content;

    p {
      padding: 1rem;
      text-transform: uppercase;
      width: 150px;
      flex-shrink: 0;
      font-weight: 600;
      font-size: 0.8125rem;
      letter-spacing: 0.39px;
      text-align: left;
    }
  }

  .records-table-row {
    display: flex;
    align-items: center;
    min-width: max-content;
    background-color: var(--surface-lower);

    p {
      padding: 1rem;
      font-size: 0.75rem;
      width: 150px;
      flex-shrink: 0;
      word-break: break-word;
      text-align: left;
    }

    .sign-out-button-wrapper {
      box-sizing: border-box;
      padding: 1rem;
      width: 150px;
      flex-shrink: 0;
    }

    .current-session-label {
      color: var(--colour-ti-muted);
      font-size: 0.75rem;
    }
  }
}

.location-attribution {
  font-size: 0.6875rem;
  line-height: 1.3;
  margin-block-start: -0.5rem;
  margin-block-end: 1rem;

  a {
    color: var(--colour-ti-muted);
  }
}

/* Overriding the link button styles */
:deep(button.base.link.filled) {
  color: var(--colour-ti-muted);
  font-size: 0.75rem;
}

@media (min-width: 768px) {
  .records-table-wrapper {
    overflow-x: visible;

    .records-table-header {
      min-width: auto;

      p {
        width: 25%;
        flex: 1;
      }
    }

    .records-table-row {
      min-width: auto;

      p {
        width: 25%;
        flex: 1;
      }

      .sign-out-button-wrapper {
        width: 25%;
        flex: 1;
      }
    }
  }
}
</style>
