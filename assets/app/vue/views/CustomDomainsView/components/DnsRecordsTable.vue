<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DetailsSummary from '@/components/DetailsSummary.vue';
import CopyValueButton from './CopyValueButton.vue';
import type { DNSRecord } from '../types';

const { t } = useI18n();

const props = defineProps<{
  records: DNSRecord[];
}>();

type RecordField = { key: 'type' | 'name' | 'content' | 'priority'; label: string };

const fields = computed<RecordField[]>(() => [
  { key: 'type', label: t('views.customDomains.dnsRecords.type') },
  { key: 'name', label: t('views.customDomains.dnsRecords.nameHost') },
  { key: 'content', label: t('views.customDomains.dnsRecords.valueData') },
  { key: 'priority', label: t('views.customDomains.dnsRecords.priority') },
]);

const fieldValue = (record: DNSRecord, key: RecordField['key']): string => record[key] || '-';

// Mobile groups the records by their type, keeping the order they first appear in
const recordsByType = computed(() => {
  const groups = new Map<string, DNSRecord[]>();
  props.records.forEach((record) => {
    groups.set(record.type, [...(groups.get(record.type) ?? []), record]);
  });
  return [...groups.entries()].map(([type, records]) => ({ type, records }));
});
</script>

<template>
  <div class="dns-records">
    <!-- Desktop -->
    <table class="records-table">
      <thead>
        <tr>
          <th v-for="field in fields" :key="field.key" scope="col" :class="`col-${field.key}`">{{ field.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(record, index) in records" :key="`${record.type}-${record.name}-${index}`">
          <td v-for="field in fields" :key="field.key" :class="`col-${field.key}`">
            <div class="cell">
              <span>{{ fieldValue(record, field.key) }}</span>
              <copy-value-button :value="fieldValue(record, field.key)" />
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Mobile -->
    <div class="records-groups">
      <details-summary
        v-for="(group, groupIndex) in recordsByType"
        :key="group.type"
        :title="`${group.type} (${group.records.length})`"
        :default-open="groupIndex === 0"
      >
        <div class="group-records">
          <dl v-for="(record, index) in group.records" :key="`${record.name}-${index}`" class="record-card">
            <div v-for="field in fields" :key="field.key" class="record-card-row">
              <div>
                <dt>{{ field.label }}</dt>
                <dd>{{ fieldValue(record, field.key) }}</dd>
              </div>
              <copy-value-button :value="fieldValue(record, field.key)" />
            </div>
          </dl>
        </div>
      </details-summary>
    </div>
  </div>
</template>

<style scoped>
.records-table {
  display: none;
}

.records-groups {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.group-records {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.record-card {
  margin: 0;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: var(--colour-neutral-lower);

  .record-card-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding-block: 0.75rem;

    &:not(:last-child) {
      border-block-end: 1px solid var(--colour-neutral-border);
    }

    &:first-child {
      padding-block-start: 0;
    }

    &:last-child {
      padding-block-end: 0;
    }
  }

  dt {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.39px;
    color: var(--colour-ti-secondary);
    margin-block-end: 0.5rem;
  }

  dd {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--colour-ti-muted);
    word-break: break-word;
  }
}

@media (min-width: 768px) {
  .records-groups {
    display: none;
  }

  .records-table {
    display: table;
    width: 100%;
    border-collapse: collapse;

    th {
      text-align: start;
      padding: 1rem;
      font-size: 0.8125rem;
      font-weight: 600;
      letter-spacing: 0.39px;
      text-transform: uppercase;
      color: var(--colour-ti-secondary);
      border-block-end: 1px solid var(--colour-neutral-border);
    }

    td {
      padding: 0.75rem 1rem;
      font-size: 0.8125rem;
      color: var(--colour-ti-secondary);
      word-break: break-word;
    }

    /* Short columns never wrap and get a minimum width; name and value share the remaining space */
    .col-type,
    .col-priority {
      width: 1%;
      white-space: nowrap;
    }

    .col-type {
      min-width: 7.5rem;
    }

    .col-priority {
      min-width: 9rem;
    }

    tbody tr:nth-child(even) {
      background-color: var(--colour-neutral-lower);
    }

    .cell {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }
  }
}
</style>
