<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DnsRecordStatus from './DnsRecordStatus.vue';
import { DNS_RECORD_STATUS } from '../types';
import type { DNSRecord } from '../types';

const { t, te } = useI18n();

const props = defineProps<{
  records: DNSRecord[];
}>();

// One row per record type, in the order the types first appear
const recordTypes = computed(() => [...new Set(props.records.map((record) => record.type))]);

const description = (type: string): string => {
  const key = `views.customDomains.verificationResults.recordTypeDescriptions.${type}`;
  return te(key) ? t(key) : '-';
};
</script>

<template>
  <div class="verified-record-types">
    <!-- Desktop -->
    <table class="types-table">
      <thead>
        <tr>
          <th scope="col">{{ t('views.customDomains.dnsRecords.status') }}</th>
          <th scope="col">{{ t('views.customDomains.dnsRecords.type') }}</th>
          <th scope="col">{{ t('views.customDomains.verificationResults.recordTypeDescription') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="type in recordTypes" :key="type">
          <td><dns-record-status :status="DNS_RECORD_STATUS.VERIFIED" /></td>
          <td>{{ type }}</td>
          <td>{{ description(type) }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Mobile -->
    <dl v-for="type in recordTypes" :key="type" class="type-card">
      <div class="type-card-row">
        <dt>{{ t('views.customDomains.dnsRecords.status') }}</dt>
        <dd><dns-record-status :status="DNS_RECORD_STATUS.VERIFIED" /></dd>
      </div>
      <div class="type-card-row">
        <dt>{{ t('views.customDomains.dnsRecords.type') }}</dt>
        <dd>{{ type }}</dd>
      </div>
      <div class="type-card-row">
        <dt>{{ t('views.customDomains.verificationResults.recordTypeDescription') }}</dt>
        <dd>{{ description(type) }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.verified-record-types {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.types-table {
  display: none;
}

.type-card {
  margin: 0;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: var(--colour-neutral-lower);

  .type-card-row {
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
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.39px;
    color: var(--colour-ti-secondary);
    margin-block-end: 0.5rem;
  }

  dd {
    margin: 0;
    font-size: 0.875rem;
    color: var(--colour-ti-secondary);
  }
}

@media (min-width: 768px) {
  .type-card {
    display: none;
  }

  .types-table {
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
      padding: 1rem;
      font-size: 0.875rem;
      color: var(--colour-ti-secondary);
      border-block-end: 1px solid var(--colour-neutral-border);
    }
  }
}
</style>
