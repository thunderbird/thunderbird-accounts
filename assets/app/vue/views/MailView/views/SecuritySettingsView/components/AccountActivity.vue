<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDevices } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import { LinkButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';

// Types
import type { ActiveSession } from '../types';

// Utils
import { formatDate } from '../utils';

const { t, locale } = useI18n();

const activeSessions = ref([]);
const loading = ref(true);
const errorMessage = ref(null);

const signOut = (id: number) => {
  if (window.confirm(t('views.mail.views.securitySettings.signOutConfirmation'))) {
    // TODO: Implement sign out logic
    console.log(`Signing out device ${id}`);
  }
};

onMounted(async () => {
  try {
    const response = await fetch('/api/v1/auth/get-active-sessions/', {
      method: 'GET',
        credentials: 'include',
      });

      const data = await response.json();

      const sortedData = data.sort((a: ActiveSession, b: ActiveSession) => b.last_access - a.last_access);

      activeSessions.value = sortedData.map((session: ActiveSession) => ({
        id: session.id,
        deviceInfo: session.device_info,
        ipAddress: session.ip_address,
        lastAccess: formatDate(new Date(session.last_access), locale.value, t),
      }));
    } catch (error) {
      errorMessage.value = t('views.mail.views.securitySettings.errorLoadingActiveSessions', error);
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
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderLastActive') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderActions') }}</p>
        </div>
  
        <div class="records-table-row" v-for="activeSession in activeSessions" :key="activeSession.id">
          <p>{{ activeSession.deviceInfo || t('views.mail.views.securitySettings.unknownDevice') }}</p>
          <p>{{ activeSession.ipAddress }}</p>
          <p>{{ activeSession.lastAccess }}</p>
          <div class="sign-out-button-wrapper">
            <link-button @click="signOut(activeSession.id)">
              {{ t('views.mail.views.securitySettings.signOut') }}
            </link-button>
          </div>
        </div>
      </div>
    </template>
    <template v-else>
      <p class="account-activity-description empty">{{ t('views.mail.views.securitySettings.noRecentDevices') }}</p>
    </template>
  </details-summary>
</template>

<style scoped>
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
    display: flex;
    align-items: center;
    border-block-end: 1px solid var(--colour-neutral-border);
    min-width: max-content;

    p {
      padding: 1rem;
      text-transform: uppercase;
      width: 150px;
      flex-shrink: 0;
      font-weight: 600;
      font-size: 0.8125rem;
      letter-spacing: 0.39px;
    }
  }

  .records-table-row {
    display: flex;
    align-items: center;
    min-width: max-content;

    p {
      padding: 1rem;
      font-size: 0.75rem;
      width: 150px;
      flex-shrink: 0;
      word-break: break-word;
    }

    &:nth-child(odd) {
      background-color: var(--colour-neutral-lower);
    }

    .sign-out-button-wrapper {
      width: 150px;
      flex-shrink: 0;
    }
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
      }
    }
  }
}
</style>