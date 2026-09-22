<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { formatTimeAgoIntl } from '@vueuse/core';
import { formatDate } from '../formatters';

const { t, locale } = useI18n();

type SecurityAccessRecord = {
  id: string;
  label: string;
  ipAddress: string;
  location: string;
  accessGiven: Date | null;
  lastAccess: Date | null;
  isCurrent?: boolean;
};

type ColumnLabels = {
  primary: string;
  location: string;
  accessGiven: string;
  lastAccess: string;
  actions: string;
};

defineProps<{
  records: SecurityAccessRecord[];
  columnLabels: ColumnLabels;
}>();

defineSlots<{
  action(props: { record: SecurityAccessRecord }): unknown;
}>();
</script>

<template>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th scope="col">{{ columnLabels.primary }}</th>
          <th scope="col">{{ columnLabels.location }}</th>
          <th scope="col">{{ columnLabels.accessGiven }}</th>
          <th scope="col">{{ columnLabels.lastAccess }}</th>
          <th scope="col">{{ columnLabels.actions }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="record in records" :key="record.id">
          <td>{{ record.label }}</td>
          <td>
            <span :title="record.ipAddress">{{ record.location }}</span>
          </td>
          <td>
            <time v-if="record.accessGiven" :datetime="record.accessGiven.toISOString()">
              {{ formatDate(record.accessGiven, locale, t) }}
            </time>
            <template v-else>{{ t('views.mail.views.securitySettings.unknownAccessGiven') }}</template>
          </td>
          <td>
            <time
              v-if="record.lastAccess"
              :datetime="record.lastAccess.toISOString()"
              :title="record.lastAccess.toLocaleString(locale, { dateStyle: 'full', timeStyle: 'long' })"
            >
              {{ formatTimeAgoIntl(record.lastAccess, {
                locale,
                relativeTimeFormatOptions: { numeric: 'auto', style: 'short' },
              }) }}
            </time>
            <template v-else>{{ t('views.mail.views.securitySettings.unknownLastAccess') }}</template>
          </td>
          <td class="action-cell">
            <slot name="action" :record="record" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrapper {
  overflow-x: auto;
  margin-block-end: 1rem;
  color: var(--colour-ti-secondary);
}

table {
  width: 100%;
  min-width: 700px;
  border-collapse: collapse;
  table-layout: fixed;
}

thead {
  border-block-end: solid 1px var(--surface-border-intense);
}

th,
td {
  box-sizing: border-box;
  padding: 1rem;
  text-align: left;
}

th {
  height: 3rem;
  color: var(--colour-ti-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.39px;
  text-transform: uppercase;
}

td {
  background-color: var(--surface-lower);
  font-size: 0.75rem;
  overflow-wrap: anywhere;
  vertical-align: middle;
}

.action-cell {
  white-space: nowrap;
}

:deep(button.base.link.filled) {
  color: var(--colour-ti-muted);
  font-size: 0.75rem;
  padding-inline: 0;
}

@media (max-width: 767px) {
  th,
  td {
    padding-inline: 0.75rem;
  }
}
</style>
