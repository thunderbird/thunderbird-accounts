<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhWarningCircle, PhWarningOctagon } from '@phosphor-icons/vue';

// Types
import { CustomDomain, DNSRecord, StaleDNSRecord, STEP, DOMAIN_STATUS, DNSRecordStatus } from '../types';
import type { DomainVerificationResult } from '../types';

// API
import { addCustomDomain, verifyDomain, getRemoteDNSRecords } from '../api';

const { t, te } = useI18n();

type InlineIssueSeverity = 'critical' | 'warning';

type InlineIssue = {
  key: string;
  severity: InlineIssueSeverity;
  text: string;
};

type DnsTableRow = {
  key: string;
  record: DNSRecord;
  issues: InlineIssue[];
  severity: InlineIssueSeverity | null;
  isStale: boolean;
  isConflict: boolean;
};

const props = defineProps<{
  customDomains: CustomDomain[];
  lastDomainRemoved?: string;
}>();

const emit = defineEmits<{
  'step-change': [step: STEP]
  'custom-domain-added': [customDomain: string]
  'custom-domain-verified': [customDomain: { name: string, status: DOMAIN_STATUS }]
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

const formatValidationError = (error: string): string => {
  const translationKey = `views.mail.sections.customDomains.verificationValidationErrors.${error}`;
  return te(translationKey) ? t(translationKey) : error;
};

const currentValue = (record: DNSRecord): string => record.existing_values?.join(', ') || '-';

const isMxRecord = (record: DNSRecord): boolean => record.type === 'MX';

const isSpfRecord = (record: DNSRecord): boolean =>
  record.type === 'TXT' && record.content.trim().toLowerCase().startsWith('v=spf1');

const spfIncludeValue = (record: DNSRecord): string =>
  record.content.split(/\s+/).find((part) => part.startsWith('include:')) ?? 'the expected include value';

const normalizeDomainName = (domainName?: string | null): string =>
  (domainName ?? '').trim().replace(/\.$/, '').toLowerCase();

const dkimRecordDomain = (record: DNSRecord): string | null => {
  if (record.type !== 'CNAME') {
    return null;
  }

  const normalizedName = normalizeDomainName(record.name);
  const domainKeySegment = '._domainkey.';
  const domainKeyIndex = normalizedName.indexOf(domainKeySegment);
  if (domainKeyIndex <= 0) {
    return null;
  }

  return normalizedName.slice(domainKeyIndex + domainKeySegment.length);
};

const isDkimRecordForCurrentDomain = (record: DNSRecord): boolean =>
  dkimRecordDomain(record) === normalizeDomainName(customDomain.value);

const missingOrConflicted = (record: DNSRecord): boolean =>
  record.status === DNSRecordStatus.MISSING || record.status === DNSRecordStatus.CONFLICT;

const missingValidationKeys = new Set(['mxLookupError', 'spfRecordNotFound', 'dkimRecordNotFound']);

const hasValidationIssue = (key: string): boolean =>
  criticalErrors.value.includes(key) || validationWarnings.value.includes(key);

const validationSeverity = (key?: string | null): InlineIssueSeverity =>
  key && criticalErrors.value.includes(key) ? 'critical' : 'warning';

const shouldAnchorDkimMissingIssue = (record: DNSRecord): boolean =>
  showMissingIssues.value
  && hasValidationIssue('dkimRecordNotFound')
  && isDkimRecordForCurrentDomain(record);

const validationResult = (data?: {
  critical_errors?: string[];
  warnings?: string[];
  dns_records?: DNSRecord[];
  stale_dns_records?: StaleDNSRecord[];
}): Pick<DomainVerificationResult, 'criticalErrors' | 'warnings' | 'dnsRecords' | 'staleDnsRecords'> => ({
  criticalErrors: data?.critical_errors ?? [],
  warnings: data?.warnings ?? [],
  dnsRecords: data?.dns_records ?? [],
  staleDnsRecords: data?.stale_dns_records ?? [],
});

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

const issueSeverity = (issues: InlineIssue[]): InlineIssueSeverity | null => {
  if (issues.some((issue) => issue.severity === 'critical')) {
    return 'critical';
  }
  if (issues.length > 0) {
    return 'warning';
  }
  return null;
};

const recordValidationKeys = (record: DNSRecord): string[] => {
  const keys = [];
  if (isMxRecord(record)) {
    keys.push('mxLookupError');
  }
  if (isSpfRecord(record)) {
    keys.push('spfRecordNotFound');
  }
  if (isDkimRecordForCurrentDomain(record)) {
    keys.push('dkimRecordNotFound');
  }
  return keys;
};

const recordStatusIssue = (record: DNSRecord): InlineIssue | null => {
  const validationKeys = recordValidationKeys(record);
  const validationKey = validationKeys.find(
    (key) => criticalErrors.value.includes(key) || validationWarnings.value.includes(key)
  );
  const missingKey = validationKey ?? validationKeys.find((key) => missingValidationKeys.has(key));

  if (isMxRecord(record) && record.status === DNSRecordStatus.CONFLICT) {
    return {
      key: 'mxLookupError',
      severity: 'critical',
      text: t('views.mail.sections.customDomains.mxRecordConflictWarning'),
    };
  }

  if (isMxRecord(record) && record.status === DNSRecordStatus.MISSING) {
    if (!showMissingIssues.value) {
      return null;
    }

    return {
      key: 'mxLookupError',
      severity: 'critical',
      text: formatValidationError('mxLookupError'),
    };
  }

  if (record.status === DNSRecordStatus.UNKNOWN && shouldAnchorDkimMissingIssue(record)) {
    return {
      key: 'dkimRecordNotFound',
      severity: validationSeverity('dkimRecordNotFound'),
      text: t('views.mail.sections.customDomains.recordMissingWarning'),
    };
  }

  if (isSpfRecord(record) && record.status === DNSRecordStatus.CONFLICT) {
    return {
      key: 'spfRecordNotFound',
      severity: 'warning',
      text: t('views.mail.sections.customDomains.spfRecordConflictWarning', { includeValue: spfIncludeValue(record) }),
    };
  }

  if (record.status === DNSRecordStatus.CONFLICT) {
    return {
      key: validationKey ?? `${record.type}-${record.name}-conflict`,
      severity: validationSeverity(validationKey),
      text: t('views.mail.sections.customDomains.recordConflictWarning', { currentValue: currentValue(record) }),
    };
  }

  if (record.status === DNSRecordStatus.MISSING) {
    if (!showMissingIssues.value) {
      return null;
    }

    return {
      key: missingKey ?? `${record.type}-${record.name}-missing`,
      severity: validationSeverity(missingKey),
      text: t('views.mail.sections.customDomains.recordMissingWarning'),
    };
  }

  return null;
};

const validationIssuesForRecord = (record: DNSRecord): InlineIssue[] =>
  recordValidationKeys(record)
    .filter((key) => criticalErrors.value.includes(key) || validationWarnings.value.includes(key))
    .filter((key) => showMissingIssues.value || !missingValidationKeys.has(key))
    .filter((key) => key === 'mxLookupError' || missingOrConflicted(record))
    .map((key) => ({
      key,
      severity: criticalErrors.value.includes(key) ? 'critical' : 'warning',
      text: formatValidationError(key),
    }));

const createDnsTableRow = (record: DNSRecord, index: number): DnsTableRow => {
  const hasConflictRows = record.status === DNSRecordStatus.CONFLICT && (record.existing_values?.length ?? 0) > 0;
  const statusIssue = hasConflictRows ? null : recordStatusIssue(record);
  const validationIssues = statusIssue || hasConflictRows ? [] : validationIssuesForRecord(record);
  const issues = statusIssue ? [statusIssue, ...validationIssues] : validationIssues;

  return {
    key: `${record.type}-${record.name}-${record.content}-${index}`,
    record,
    issues,
    severity: issueSeverity(issues),
    isStale: false,
    isConflict: false,
  };
};

const conflictSeverity = (record: DNSRecord): InlineIssueSeverity =>
  isMxRecord(record) || recordValidationKeys(record).some((key) => criticalErrors.value.includes(key))
    ? 'critical'
    : 'warning';

const createConflictingRecord = (record: DNSRecord, existingValue: string): DNSRecord => {
  const valueParts = existingValue.trim().split(/\s+/);

  if (record.type === 'MX' && valueParts.length > 1) {
    return {
      ...record,
      content: valueParts.slice(1).join(' '),
      priority: valueParts[0],
      existing_values: [existingValue],
    };
  }

  if (record.type === 'SRV' && valueParts.length > 3) {
    return {
      ...record,
      content: valueParts.slice(1).join(' '),
      priority: valueParts[0],
      existing_values: [existingValue],
    };
  }

  return {
    ...record,
    content: existingValue,
    priority: '-',
    existing_values: [existingValue],
  };
};

const createConflictDnsTableRows = (record: DNSRecord, index: number): DnsTableRow[] => {
  if (record.status !== DNSRecordStatus.CONFLICT || !record.existing_values?.length) {
    return [];
  }

  const statusIssue = recordStatusIssue(record);
  const validationIssues = statusIssue ? [] : validationIssuesForRecord(record);
  const issues = statusIssue ? [statusIssue, ...validationIssues] : validationIssues;

  return record.existing_values.map((existingValue, conflictIndex) => ({
    key: `conflict-${record.type}-${record.name}-${existingValue}-${index}-${conflictIndex}`,
    record: createConflictingRecord(record, existingValue),
    issues: conflictIndex === 0 ? issues : [],
    severity: conflictSeverity(record),
    isStale: false,
    isConflict: true,
  }));
};

const createDnsTableRows = (record: DNSRecord, index: number): DnsTableRow[] => [
  createDnsTableRow(record, index),
  ...createConflictDnsTableRows(record, index),
];

const createStaleDnsTableRow = (record: StaleDNSRecord): DnsTableRow => {
  const isSrv = record.code === 'autodiscoverSrvUnexpected';
  const validationKey = isSrv ? 'autodiscoverSrvRecordFound' : 'autodiscoverRecordFound';
  const issues = [
    {
      key: validationKey,
      severity: 'critical' as const,
      text: formatValidationError(validationKey),
    },
  ];

  return {
    key: `stale-${record.code}-${record.type}-${record.name}`,
    record: {
      type: record.type,
      name: record.name,
      content: record.existing_values.join(', '),
      priority: '-',
      status: DNSRecordStatus.CONFLICT,
      existing_values: record.existing_values,
    },
    issues,
    severity: 'critical',
    isStale: true,
    isConflict: false,
  };
};

const staleAddressRows = computed(() =>
  staleDnsRecords.value
    .filter((record) => record.code === 'autodiscoverCnameUnexpected')
    .map(createStaleDnsTableRow)
);

const staleSrvRows = computed(() =>
  staleDnsRecords.value
    .filter((record) => record.code === 'autodiscoverSrvUnexpected')
    .map(createStaleDnsTableRow)
);

const dnsTableRows = computed(() => {
  const expectedRows = recordsInfo.value.flatMap(createDnsTableRows);
  const rows = [];
  let insertedAddressRows = false;
  let insertedSrvRows = false;

  expectedRows.forEach((row, index) => {
    rows.push(row);
    const nextRow = expectedRows[index + 1];

    if (!insertedSrvRows && row.record.type === 'SRV' && nextRow?.record.type !== 'SRV') {
      rows.push(...staleSrvRows.value);
      insertedSrvRows = true;
    }

    if (!insertedAddressRows && row.record.type === 'CNAME' && nextRow?.record.type !== 'CNAME') {
      rows.push(...staleAddressRows.value);
      insertedAddressRows = true;
    }
  });

  if (!insertedSrvRows) {
    rows.push(...staleSrvRows.value);
  }
  if (!insertedAddressRows) {
    rows.push(...staleAddressRows.value);
  }

  return rows;
});

const anchoredValidationKeys = computed(() => new Set(dnsTableRows.value.flatMap((row) => row.issues.map((issue) => issue.key))));

const unanchoredValidationIssues = computed<InlineIssue[]>(() => [
  ...criticalErrors.value
    .filter((key) => !anchoredValidationKeys.value.has(key))
    .filter((key) => showMissingIssues.value || !missingValidationKeys.has(key))
    .map((key) => ({
      key,
      severity: 'critical' as const,
      text: formatValidationError(key),
    })),
  ...validationWarnings.value
    .filter((key) => !anchoredValidationKeys.value.has(key))
    .filter((key) => showMissingIssues.value || !missingValidationKeys.has(key))
    .map((key) => ({
      key,
      severity: 'warning' as const,
      text: formatValidationError(key),
    })),
]);

const handleDNSRecords = async (domainName: string) => {
  try {
    const remoteDNSRecords = await getRemoteDNSRecords(domainName);

    if (remoteDNSRecords.success) {
      applyVerificationResult(domainName, validationResult(remoteDNSRecords), { showMissingIssues: false });
    } else {
      console.error(remoteDNSRecords.error);
      customDomainError.value = remoteDNSRecords.error;
    }
  } catch (error) {
    console.error(error);
    customDomainError.value = String(error);
  }
}

const onCreateCustomDomain = async () => {
  const submittedDomain = customDomain.value ?? '';
  isAddingCustomDomain.value = true;

  try {
    const data = await addCustomDomain(submittedDomain);

    if (data.success) {
      const domainName = data.domain_name ?? submittedDomain;
      customDomain.value = domainName;
      customDomainError.value = null;
      domainAlreadyConfigured.value = false;
      emit('custom-domain-added', domainName);
      await handleDNSRecords(domainName);
    } else if (data.code === 'domain_already_configured') {
      console.error(data.error);
      customDomainError.value = null;
      domainAlreadyConfigured.value = true;
    } else {
      console.error(data.error);
      domainAlreadyConfigured.value = false;
      customDomainError.value = data.error ?? '';
    }
  } catch (error) {
    console.error(error);
    domainAlreadyConfigured.value = false;
    customDomainError.value = String(error);
  } finally {
    isAddingCustomDomain.value = false;
  }
};

const onVerifyDomain = async () => {
  isVerifyingDomain.value = true;

  try {
    const data = await verifyDomain(customDomain.value);

    applyVerificationResult(customDomain.value, validationResult(data), {
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
  const verificationResult = verificationResultsByDomain.value[domainName];
  if (verificationResult) {
    applyVerificationResult(domainName, verificationResult, { showMissingIssues: true });
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

watch(step, (newStep) => {
  emit('step-change', newStep);
}, { immediate: true });

watch(() => props.lastDomainRemoved, (newLastDomainRemoved) => {
  // If we just removed the domain we were adding, reset the step to initial
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
}, { immediate: true });
</script>

<template>
  <template v-if="step === STEP.INITIAL">
    <primary-button
      variant="outline"
      @click="step = STEP.ADD"
      v-if="customDomains.length < maxCustomDomains"
    >
      {{ t('views.mail.sections.customDomains.addDomain') }}
    </primary-button>
  </template>

  <template v-else-if="step === STEP.ADD">
    <form @submit.prevent="onCreateCustomDomain">
      <text-input
        :placeholder="t('views.mail.sections.customDomains.domainPlaceholder')"
        name="custom-domain"
        :help="t('views.mail.sections.customDomains.domainHelp')"
        :error="customDomainError"
        class="custom-domain-text-input"
        v-model="customDomain"
      >
        {{ t('views.mail.sections.customDomains.enterCustomDomain') }}
      </text-input>
  
      <notice-bar :type="NoticeBarTypes.Critical" v-if="domainAlreadyConfigured" class="domain-already-configured-notice-bar">
        <i18n-t keypath="views.mail.sections.customDomains.domainAlreadyConfigured" tag="span">
          <template #link>
             <router-link to="/contact">{{ t('views.mail.sections.customDomains.reachOutToSupport') }}</router-link>
          </template>
        </i18n-t>
      </notice-bar>

      <primary-button variant="outline" @click="onCreateCustomDomain" :disabled="isAddingCustomDomain">
        {{ t('views.mail.sections.customDomains.continue') }}
      </primary-button>
    </form>
  </template>

  <template v-else-if="step === STEP.VERIFY_DOMAIN">
    <h3>{{ t('views.mail.sections.customDomains.verifyStepTitle') }}</h3>
    <div class="verify-step-list">
      <h4>{{ t('views.mail.sections.customDomains.verifyStepOneTitle') }}</h4>
      <p>{{ t('views.mail.sections.customDomains.verifyStepOne') }}</p>
      <h4>{{ t('views.mail.sections.customDomains.verifyStepTwoTitle') }}</h4>
      <p>{{ t('views.mail.sections.customDomains.verifyStepTwo') }}</p>
      <h4>{{ t('views.mail.sections.customDomains.verifyStepThreeTitle') }}</h4>
      <p>{{ t('views.mail.sections.customDomains.verifyStepThree') }}</p>
      <p class="verify-step-note">
        <strong>{{ t('views.mail.sections.customDomains.verifyStepNoteTip') }}</strong>
        {{ t('views.mail.sections.customDomains.verifyStepNote') }}
      </p>
    </div>

    <div class="records-table-wrapper">
      <div class="records-table-header">
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderType') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderNameHost') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderValueData') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderPriority') }}</p>
      </div>
      <div
        class="records-table-row"
        :class="{
          'record-critical': row.severity === 'critical',
          'record-warning': row.severity === 'warning',
          'record-stale': row.isStale,
          'record-conflict': row.isConflict,
        }"
        v-for="row in dnsTableRows"
        :key="row.key"
      >
        <div class="records-table-row-cells">
          <p>{{ row.record.type }}</p>
          <p>{{ row.record.name }}</p>
          <p>{{ row.record.content }}</p>
          <p>{{ row.record.priority || '-' }}</p>
        </div>

        <div
          v-if="row.issues.length > 0"
          class="record-inline-issues"
        >
          <p
            v-for="issue in row.issues"
            :key="issue.key"
            class="inline-issue"
            :class="`inline-issue-${issue.severity}`"
          >
            <ph-warning-octagon v-if="issue.severity === 'critical'" size="18" weight="fill" aria-hidden="true" />
            <ph-warning-circle v-else size="18" weight="fill" aria-hidden="true" />
            <span>{{ issue.text }}</span>
          </p>
        </div>
      </div>

      <div class="records-table-footer" v-if="unanchoredValidationIssues.length > 0">
        <p
          v-for="issue in unanchoredValidationIssues"
          :key="issue.key"
          class="inline-issue"
          :class="`inline-issue-${issue.severity}`"
        >
          <ph-warning-octagon v-if="issue.severity === 'critical'" size="18" weight="fill" aria-hidden="true" />
          <ph-warning-circle v-else size="18" weight="fill" aria-hidden="true" />
          <span>{{ issue.text }}</span>
        </p>
      </div>
    </div>

    <!-- TODO: Uncomment this once we have the task / job to automatically verify domains -->
    <!-- <notice-bar :type="NoticeBarTypes.Info" class="verify-step-notice-bar" v-if="showNoticeBar">
      <strong>{{ t('views.mail.sections.customDomains.verifyStepInfoTitle') }}</strong>
      <p>{{ t('views.mail.sections.customDomains.verifyStepInfoDescription') }}</p>

      <template #cta>
        <button class="close-button" @click="showNoticeBar = false">
          <ph-x size="24" />
        </button>
      </template>
    </notice-bar> -->

    <primary-button
      class="verify-step-button"
      @click="onVerifyDomain"
      :disabled="isVerifyingDomain"
    >
      {{ t('views.mail.sections.customDomains.verifyStepButton') }}
    </primary-button>
  </template>
</template>

<style scoped>
.custom-domain-text-input {
  margin-block-end: 1.5rem;
}

.domain-already-configured-notice-bar {
  margin-block-end: 1.5rem;

  a {
    color: var(--colour-ti-secondary);
  }
}

h3 {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.48px;
  margin-block-end: 1.5rem;
}

.verify-step-list {
  display: flex;
  flex-direction: column;
  line-height: 1.32;
  color: var(--colour-ti-secondary);
  margin-block-end: 1.5rem;

  h4 {
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.32;
    margin-block-end: 0.25rem;
  }

  p {
    margin-inline-start: 1rem;
    margin-block-end: 1.5rem;
    font-size: 0.875rem;

    &:not(:first-of-type) {
      margin-inline-start: 1.25rem;
    }
  }

  .verify-step-note {
    font-size: 0.875rem;
    line-height: normal;
    margin: 0;
  }
}

.records-table-wrapper {
  overflow-x: auto;
  margin-block-end: 1.5rem;
}

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
  flex-direction: column;
  min-width: max-content;
  border-inline-start: 0.25rem solid transparent;

  &:nth-child(odd) {
    background-color: var(--colour-neutral-lower);
  }

  &.record-warning {
    border-inline-start-color: var(--colour-warning-default);
    background-color: var(--colour-warning-soft);
  }

  &.record-critical {
    border-inline-start-color: var(--colour-danger-default);
    background-color: var(--colour-danger-soft);
  }

  &.record-stale {
    .records-table-row-cells p:first-child {
      font-weight: 600;
    }
  }

  &.record-conflict {
    .records-table-row-cells p {
      font-weight: 600;
    }
  }
}

.records-table-row-cells {
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
}

.record-inline-issues,
.records-table-footer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1rem 1rem;
}

.records-table-footer {
  min-width: max-content;
  border-block-start: 1px solid var(--colour-neutral-border);
  padding-block-start: 1rem;
}

.inline-issue {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.35;

  svg {
    flex: 0 0 auto;
    margin-block-start: 0.0625rem;
  }
}

.inline-issue-critical {
  color: var(--colour-danger-default);
}

.inline-issue-warning {
  color: var(--colour-ti-warning);
}

.verify-step-notice-bar {
  margin-block-end: 1.5rem;

  .close-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem;
    border: none;
    border-radius: 300px;
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05);
    background-color: rgba(0, 0, 0, 0.05);
    color: var(--colour-ti-secondary);
    cursor: pointer;

    &:hover {
      background-color: rgba(0, 0, 0, 0.1);
    }

    &:active {
      background-color: rgba(0, 0, 0, 0.2);
    }
  }
}

.verify-step-button {
  margin-block-start: 1.5rem;
}

@media (min-width: 768px) {
  .custom-domain-text-input {
    max-width: 50%;
  }

  .domain-already-configured-notice-bar {
    max-width: 50%;
  }

  .records-table-wrapper {
    overflow-x: visible;
  }

  .records-table-header {
    min-width: auto;

    p {
      width: 25%;
      flex: 1;
    }
  }

  .records-table-row {
    min-width: auto;
  }

  .records-table-row-cells {
    min-width: auto;

    p {
      width: 25%;
      flex: 1;
    }
  }
}
</style>
