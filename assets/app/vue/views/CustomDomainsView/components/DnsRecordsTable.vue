<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCaretDown, PhCaretUp } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';
import CopyValueButton from './CopyValueButton.vue';
import DnsRecordStatus from './DnsRecordStatus.vue';
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

// A status column is only shown for records that have been through verification
const showStatus = computed(() => props.records.some((record) => record.status));

const rows = computed(() => props.records.map((record, index) => ({ key: `${record.type}-${record.name}-${index}`, record })));

// Issue messages are expanded unless the user collapses them
const collapsedRows = ref<Set<string>>(new Set());

const toggleRow = (key: string) => {
  const next = new Set(collapsedRows.value);
  if (!next.delete(key)) {
    next.add(key);
  }
  collapsedRows.value = next;
};

// Mobile groups the records by their type, keeping the order they first appear in
const recordsByType = computed(() => {
  const groups = new Map<string, DNSRecord[]>();
  props.records.forEach((record) => {
    groups.set(record.type, [...(groups.get(record.type) ?? []), record]);
  });
  return [...groups.entries()].map(([type, records]) => ({
    type,
    records,
    hasIssue: records.some((record) => record.issue),
  }));
});

const rootRef = ref<HTMLElement | null>(null);

// Scrolls to the first record that needs attention, whichever layout is currently visible
const scrollToFirstIssue = () => {
  const target = [...(rootRef.value?.querySelectorAll<HTMLElement>('[data-issue]') ?? [])]
    .find((element) => element.offsetParent !== null);
  target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

defineExpose({ scrollToFirstIssue });
</script>

<template>
  <div ref="rootRef" class="dns-records">
    <!-- Desktop -->
    <table class="records-table">
      <thead>
        <tr>
          <th v-if="showStatus" scope="col" class="col-status">{{ t('views.customDomains.dnsRecords.status') }}</th>
          <th v-for="field in fields" :key="field.key" scope="col" :class="`col-${field.key}`">{{ field.label }}</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="{ key, record } in rows" :key="key">
          <tr :class="{ 'has-issue-message': record.issue && !collapsedRows.has(key) }" :data-issue="record.issue ? '' : undefined">
            <td v-if="showStatus" class="col-status">
              <div class="status-cell">
                <button
                  v-if="record.issue"
                  type="button"
                  class="issue-toggle"
                  :aria-expanded="!collapsedRows.has(key)"
                  :aria-label="t('views.customDomains.dnsRecords.toggleIssue')"
                  @click="toggleRow(key)"
                >
                  <ph-caret-down v-if="collapsedRows.has(key)" size="16" aria-hidden="true" />
                  <ph-caret-up v-else size="16" aria-hidden="true" />
                </button>
                <dns-record-status v-if="record.status" :status="record.status" />
              </div>
            </td>
            <td v-for="field in fields" :key="field.key" :class="`col-${field.key}`">
              <div class="cell">
                <span>{{ fieldValue(record, field.key) }}</span>
                <copy-value-button :value="fieldValue(record, field.key)" />
              </div>
            </td>
          </tr>
          <tr v-if="record.issue && !collapsedRows.has(key)" class="issue-row">
            <td :colspan="fields.length + 1">
              <p class="issue-message" :class="record.status">{{ record.issue }}</p>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <!-- Mobile -->
    <div class="records-groups">
      <details-summary
        v-for="(group, groupIndex) in recordsByType"
        :key="group.type"
        :title="`${group.type} (${group.records.length})`"
        :default-open="group.hasIssue || (!showStatus && groupIndex === 0)"
      >
        <div class="group-records">
          <dl
            v-for="(record, index) in group.records"
            :key="`${record.name}-${index}`"
            class="record-card"
            :data-issue="record.issue ? '' : undefined"
          >
            <div v-if="record.status" class="record-card-row">
              <div>
                <dt>{{ t('views.customDomains.dnsRecords.status') }}</dt>
                <dd><dns-record-status :status="record.status" /></dd>
              </div>
            </div>
            <div v-for="field in fields" :key="field.key" class="record-card-row">
              <div>
                <dt>{{ field.label }}</dt>
                <dd>{{ fieldValue(record, field.key) }}</dd>
              </div>
              <copy-value-button :value="fieldValue(record, field.key)" />
            </div>
            <p v-if="record.issue" class="issue-message" :class="record.status">{{ record.issue }}</p>
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
    border-block-end: 1px solid var(--colour-neutral-border);

    &:first-child {
      padding-block-start: 0;
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
    overflow-wrap: anywhere;
  }

  /* The last field has no divider unless an issue message follows it */
  .record-card-row:last-of-type:last-child {
    border-block-end: none;
    padding-block-end: 0;
  }

  .issue-message {
    margin-block-start: 0.75rem;
  }
}

.issue-message {
  margin: 0;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.8125rem;
  line-height: 1.35;
  color: var(--colour-ti-secondary);

  &.action-required {
    background-color: var(--colour-warning-soft);
  }

  &.not-found {
    background-color: var(--colour-danger-soft);
  }
}

@media (min-width: 768px) {
  .records-groups {
    display: none;
  }

  .records-table {
    display: table;
    table-layout: fixed;
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
      overflow-wrap: anywhere;
    }

    /* Fixed layout keeps the table inside its container: the short columns get set widths (never wrapping)
       and name and value split whatever remains, wrapping long values instead of stretching the table */
    .col-status,
    .col-type,
    .col-priority {
      white-space: nowrap;
    }

    .col-status {
      width: 11rem;
    }

    .col-type {
      width: 7.5rem;
    }

    .col-priority {
      width: 9rem;
    }

    tbody tr:nth-child(even):not(.issue-row) {
      background-color: var(--colour-neutral-lower);
    }

    .has-issue-message td {
      padding-block-end: 0.25rem;
    }

    .issue-row td {
      padding-block: 0 0.75rem;
    }

    /* The value takes the free space so every copy button lines up on the column's right edge */
    .cell {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      > span {
        flex: 1;
        min-width: 0;
      }
    }

    .status-cell {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .issue-toggle {
      all: unset;
      box-sizing: border-box;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.5rem;
      height: 1.5rem;
      border-radius: 0.25rem;
      color: var(--colour-ti-base);
      cursor: pointer;

      &:focus-visible {
        outline: 2px solid var(--colour-primary-default);
      }
    }
  }
}
</style>
