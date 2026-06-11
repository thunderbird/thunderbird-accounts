<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';

import { CustomDomain, StaleDNSRecord, STEP, DOMAIN_STATUS, DNSRecord } from '../types';
import type { DomainVerificationResult, InlineIssue, DecoratedDnsTableRow } from '../types';

import { addCustomDomain, verifyDomain, getRemoteDNSRecords } from '../api';
import { buildDecoratedDnsTableRows, buildUnanchoredValidationIssues, validationResultFromApi } from '../utils';

import CustomDomainAddStep from './CustomDomainAddStep.vue';
import CustomDomainVerifyStep from './CustomDomainVerifyStep.vue';

const { t, te } = useI18n();

const props = defineProps<{
  customDomains: CustomDomain[];
  lastDomainRemoved?: string;
}>();

const emit = defineEmits<{
  'step-change': [step: STEP];
  'custom-domain-added': [customDomain: string];
  'custom-domain-verified': [customDomain: { name: string; status: DOMAIN_STATUS }];
}>();

const step = ref<STEP>(STEP.INITIAL);
const customDomain = ref<string | null>(null);
const isAddingCustomDomain = ref(false);
const isVerifyingDomain = ref(false);
const customDomainError = ref<string>(null);
const domainAlreadyConfigured = ref(false);

const maxCustomDomains = window._page?.maxCustomDomains;

const recordsInfo = ref<DNSRecord[]>([]);
const staleDnsRecords = ref<StaleDNSRecord[]>([]);
const criticalErrors = ref<string[]>([]);
const validationWarnings = ref<string[]>([]);
const showMissingIssues = ref(false);
const verificationResultsByDomain = ref<Record<string, Omit<DomainVerificationResult, 'domainName'>>>({});

const dnsTableState = computed(() => ({
  customDomain: customDomain.value ?? '',
  criticalErrors: criticalErrors.value,
  validationWarnings: validationWarnings.value,
  showMissingIssues: showMissingIssues.value,
}));

const dnsTableI18n = { t, te };

const applyVerificationResult = (
  domainName: string,
  result: Omit<DomainVerificationResult, 'domainName'>,
  options: { showMissingIssues: boolean; cacheResult?: boolean }
) => {
  customDomain.value = domainName;
  recordsInfo.value = result.dnsRecords;
  staleDnsRecords.value = result.staleDnsRecords;
  criticalErrors.value = result.criticalErrors;
  validationWarnings.value = result.warnings;
  showMissingIssues.value = options.showMissingIssues;
  step.value = STEP.VERIFY_DOMAIN;

  if (options.cacheResult) {
    verificationResultsByDomain.value = {
      ...verificationResultsByDomain.value,
      [domainName]: result,
    };
  }
};

const dnsTableRows = computed<DecoratedDnsTableRow[]>(() =>
  buildDecoratedDnsTableRows(recordsInfo.value, staleDnsRecords.value, dnsTableState.value, dnsTableI18n)
);

const anchoredValidationKeys = computed(
  () => new Set(dnsTableRows.value.flatMap((row) => row.issues.map((issue) => issue.key)))
);

const unanchoredValidationIssues = computed<InlineIssue[]>(() =>
  buildUnanchoredValidationIssues(
    criticalErrors.value,
    validationWarnings.value,
    anchoredValidationKeys.value,
    showMissingIssues.value,
    dnsTableI18n
  )
);

const handleDNSRecords = async (domainName: string) => {
  try {
    const remoteDNSRecords = await getRemoteDNSRecords(domainName);

    if (remoteDNSRecords.success) {
      applyVerificationResult(domainName, validationResultFromApi(remoteDNSRecords), { showMissingIssues: false });
    } else {
      console.error(remoteDNSRecords.error);
      customDomainError.value = remoteDNSRecords.error;
    }
  } catch (error) {
    console.error(error);
    customDomainError.value = error;
  }
};

const onCreateCustomDomain = async () => {
  if (props.customDomains.some((domain) => domain.name === customDomain.value)) {
    customDomainError.value = t('views.mail.sections.customDomains.domainAlreadyExists');
    return;
  }

  isAddingCustomDomain.value = true;

  try {
    const data = await addCustomDomain(customDomain.value);

    if (data.success) {
      emit('custom-domain-added', customDomain.value);
      await handleDNSRecords(customDomain.value);
    } else if (data.code === 'domain_already_configured') {
      console.error(data.error);
      domainAlreadyConfigured.value = true;
    } else {
      console.error(data.error);
      customDomainError.value = data.error;
    }
  } catch (error) {
    console.error(error);
    customDomainError.value = error;
  } finally {
    isAddingCustomDomain.value = false;
  }
};

const onVerifyDomain = async () => {
  isVerifyingDomain.value = true;

  try {
    const data = await verifyDomain(customDomain.value);

    applyVerificationResult(customDomain.value, validationResultFromApi(data), {
      showMissingIssues: true,
      cacheResult: true,
    });

    if (data.success) {
      emit('custom-domain-verified', { name: customDomain.value, status: DOMAIN_STATUS.VERIFIED });
      customDomainError.value = null;
      domainAlreadyConfigured.value = false;
    } else {
      emit('custom-domain-verified', { name: customDomain.value, status: DOMAIN_STATUS.FAILED });
    }
  } catch (error) {
    emit('custom-domain-verified', { name: customDomain.value, status: DOMAIN_STATUS.FAILED });
    customDomainError.value = String(error);
  } finally {
    isVerifyingDomain.value = false;
  }
};

const viewDnsRecords = async (domainName: string) => {
  customDomain.value = domainName;
  const cachedResult = verificationResultsByDomain.value[domainName];
  if (cachedResult) {
    applyVerificationResult(domainName, cachedResult, { showMissingIssues: true });
    return;
  }

  await handleDNSRecords(domainName);
};

const showVerificationResult = (result: DomainVerificationResult) => {
  applyVerificationResult(result.domainName, result, { showMissingIssues: true, cacheResult: true });
};

defineExpose({
  viewDnsRecords,
  showVerificationResult,
});

watch(
  step,
  (newStep) => {
    emit('step-change', newStep);
  },
  { immediate: true }
);

watch(
  () => props.lastDomainRemoved,
  (newLastDomainRemoved) => {
    if (newLastDomainRemoved === customDomain.value) {
      step.value = STEP.INITIAL;
      customDomain.value = null;
      customDomainError.value = null;
      domainAlreadyConfigured.value = false;
      staleDnsRecords.value = [];
      criticalErrors.value = [];
      validationWarnings.value = [];
      showMissingIssues.value = false;
      delete verificationResultsByDomain.value[newLastDomainRemoved];
    }
  },
  { immediate: true }
);
</script>

<template>
  <template v-if="step === STEP.INITIAL">
    <primary-button variant="outline" @click="step = STEP.ADD" v-if="customDomains.length < maxCustomDomains">
      {{ t('views.mail.sections.customDomains.addDomain') }}
    </primary-button>
  </template>

  <custom-domain-add-step
    v-else-if="step === STEP.ADD"
    v-model:custom-domain="customDomain"
    :custom-domain-error="customDomainError"
    :domain-already-configured="domainAlreadyConfigured"
    :is-adding-custom-domain="isAddingCustomDomain"
    @submit="onCreateCustomDomain"
  />

  <custom-domain-verify-step
    v-else-if="step === STEP.VERIFY_DOMAIN"
    :dns-table-rows="dnsTableRows"
    :unanchored-validation-issues="unanchoredValidationIssues"
    :is-verifying-domain="isVerifyingDomain"
    @verify="onVerifyDomain"
  />
</template>
