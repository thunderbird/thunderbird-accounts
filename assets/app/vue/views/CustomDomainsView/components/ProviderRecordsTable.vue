<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DetailsSummary from '@/components/DetailsSummary.vue';
import CopyValueButton from './CopyValueButton.vue';
import { buildProviderRecordGroups } from '../providerRecords';
import type { DNSRecord, DnsProviderConfig, ProviderRecordGroup } from '../types';

const { t, locale } = useI18n();

const props = defineProps<{
  records: DNSRecord[];
  domainName: string;
  provider: DnsProviderConfig;
}>();

const NARROW_COLUMN_WIDTHS: Record<string, string> = {
  Type: '9.5rem',
  Priority: '8rem',
  Weight: '7rem',
  Port: '7rem',
};

const groups = computed(() => buildProviderRecordGroups(props.records, props.domainName, props.provider));

// "Priority and Weight are 0": fields sharing a value are listed together
const sharedMessages = (group: ProviderRecordGroup) => {
  const labelsByValue = new Map<string, string[]>();
  group.sharedFields.forEach(({ label, value }) => {
    labelsByValue.set(value, [...(labelsByValue.get(value) ?? []), label]);
  });

  const entries = [...labelsByValue.entries()];
  return entries.map(([value, labels], index) => ({
    value,
    separator: index < entries.length - 1 ? ', ' : ` ${t('views.customDomains.dnsRecords.sharedSuffix', { type: group.type })}`,
    count: labels.length,
    // Each label comes back as its own part so it can be bolded without v-html
    parts: new Intl.ListFormat(locale.value, { style: 'long', type: 'conjunction' }).formatToParts(labels),
  }));
};
</script>

<template>
  <div class="provider-records">
    <details-summary
      v-for="(group, groupIndex) in groups"
      :key="group.type"
      :title="`${group.type} (${group.rows.length})`"
      :default-open="groupIndex === 0"
    >
      <p v-if="group.sharedFields.length" class="shared-fields">
        <template v-for="message in sharedMessages(group)" :key="message.value">
          <i18n-t keypath="views.customDomains.dnsRecords.sharedValue" :plural="message.count" tag="span">
            <template #fields>
              <template v-for="(part, partIndex) in message.parts" :key="partIndex">
                <strong v-if="part.type === 'element'">{{ part.value }}</strong>
                <template v-else>{{ part.value }}</template>
              </template>
            </template>
            <template #value><strong>{{ message.value }}</strong></template>
          </i18n-t>{{ message.separator }}
        </template>
      </p>

      <!-- Desktop -->
      <table class="records-table">
        <colgroup>
          <col v-for="column in group.columns" :key="column" :style="{ width: NARROW_COLUMN_WIDTHS[column] }" />
        </colgroup>
        <thead>
          <tr>
            <th v-for="column in group.columns" :key="column" scope="col">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in group.rows" :key="rowIndex">
            <td v-for="cell in row" :key="cell.label">
              <div class="cell">
                <span class="value" :class="{ blank: !cell.value }">
                  {{ cell.value || t('views.customDomains.dnsRecords.leaveBlank') }}
                </span>
                <span v-if="cell.hint" class="hint">{{ cell.hint }}</span>
                <copy-value-button v-if="cell.value" :value="cell.value" :label="`${t('views.customDomains.dnsRecords.copy')} ${cell.label}`" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Mobile -->
      <dl v-for="(row, rowIndex) in group.rows" :key="rowIndex" class="record-card">
        <div v-for="cell in row" :key="cell.label" class="record-card-row">
          <div>
            <dt>{{ cell.label }}</dt>
            <dd :class="{ blank: !cell.value }">
              {{ cell.value || t('views.customDomains.dnsRecords.leaveBlank') }}
              <span v-if="cell.hint" class="hint">{{ cell.hint }}</span>
            </dd>
          </div>
          <copy-value-button v-if="cell.value" :value="cell.value" :label="`${t('views.customDomains.dnsRecords.copy')} ${cell.label}`" />
        </div>
      </dl>
    </details-summary>
  </div>
</template>

<style scoped>
.provider-records {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.blank {
  font-style: italic;
  color: var(--colour-ti-muted);
}

.shared-fields {
  margin: 0 0 1rem;
  color: var(--colour-ti-secondary);
}

.hint {
  font-size: 0.75rem;
  color: var(--colour-ti-muted);
}

.records-table {
  display: none;
}

.record-card {
  margin: 0 0 1rem;
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

    &:last-child {
      padding-block-end: 0;
      border-block-end: none;
    }
  }

  dt {
    margin-block-end: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.39px;
    color: var(--colour-ti-secondary);
  }

  dd {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--colour-ti-muted);
    overflow-wrap: anywhere;
  }
}

@media (min-width: 768px) {
  .record-card {
    display: none;
  }

  .records-table {
    display: table;
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;

    th {
      padding: 1rem;
      text-align: start;
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

    tbody tr:nth-child(even) {
      background-color: var(--colour-neutral-lower);
    }

    .cell {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .value {
        flex: 1;
        min-width: 0;
      }
    }
  }
}
</style>
