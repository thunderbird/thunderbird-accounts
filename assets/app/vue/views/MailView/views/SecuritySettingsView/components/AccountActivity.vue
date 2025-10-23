<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhDevices } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import { LinkButton } from '@thunderbirdops/services-ui';

const { t } = useI18n();

const accountActivityRecords = [
  {
    id: 1,
    device: 'macOS – Thunderbird',
    location: 'Berlin, Germany',
    lastActive: 'Today at 10:24 AM',
  },
  {
    id: 2,
    device: 'Windows – Outlook',
    location: 'San Francisco, USA',
    lastActive: 'Yesterday at 8:02 PM',
  },
  {
    id: 3,
    device: 'Android – Gmail App',
    location: 'Tokyo, Japan',
    lastActive: 'Jun 24, 2:15 AM',
  },
  {
    id: 4,
    device: 'Unknown Device – IMAP',
    location: 'Paris, France',
    lastActive: 'Jun 22, 6:45 PM',
  },
];

const signOut = (id: number) => {
  // TODO: Implement sign out logic
  console.log(`Signing out device ${id}`);
};
</script>

<template>
  <details-summary :title="t('views.mail.views.securitySettings.accountActivity')" :expandable="false" default-open>
    <template #icon>
      <ph-devices size="24" />
    </template>

    <template v-if="accountActivityRecords.length > 0">
      <p class="account-activity-description">{{ t('views.mail.views.securitySettings.accountActivityDescription') }}</p>
  
      <div class="records-table-wrapper" >
        <div class="records-table-header">
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderDevice') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderLocation') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderLastActive') }}</p>
          <p>{{ t('views.mail.views.securitySettings.recordsTableHeaderActions') }}</p>
        </div>
  
        <div class="records-table-row" v-for="record in accountActivityRecords" :key="record.id">
          <p>{{ record.device }}</p>
          <p>{{ record.location }}</p>
          <p>{{ record.lastActive }}</p>
          <div class="sign-out-button-wrapper">
            <link-button @click="signOut(record.id)">
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