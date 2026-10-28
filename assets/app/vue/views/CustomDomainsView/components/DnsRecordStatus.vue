<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCheckCircle, PhWarning, PhWarningCircle } from '@phosphor-icons/vue';
import { DNS_RECORD_STATUS } from '../types';

const { t } = useI18n();

const props = defineProps<{
  status: DNS_RECORD_STATUS;
}>();

const config = computed(() => ({
  [DNS_RECORD_STATUS.VERIFIED]: { icon: PhCheckCircle, label: t('views.customDomains.dnsRecords.statusVerified') },
  [DNS_RECORD_STATUS.ACTION_REQUIRED]: { icon: PhWarning, label: t('views.customDomains.dnsRecords.statusActionRequired') },
  [DNS_RECORD_STATUS.NOT_FOUND]: { icon: PhWarningCircle, label: t('views.customDomains.dnsRecords.statusNotFound') },
}[props.status]));
</script>

<template>
  <span class="dns-record-status" :class="status">
    <component :is="config.icon" size="16" aria-hidden="true" />
    {{ config.label }}
  </span>
</template>

<style scoped>
.dns-record-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.688rem;
  white-space: nowrap;

  &.verified {
    color: var(--colour-ti-success);
  }

  &.action-required {
    color: var(--colour-ti-warning);
    background-color: var(--colour-warning-soft);
  }

  &.not-found {
    color: var(--colour-danger-default);
    background-color: var(--colour-danger-soft);
  }
}
</style>
