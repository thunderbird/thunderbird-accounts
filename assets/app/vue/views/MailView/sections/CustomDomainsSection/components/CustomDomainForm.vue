<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import {
  PhCheck,
  PhCheckCircle,
  PhCopySimple,
  PhInfo,
  PhWarning,
  PhWarningCircle,
  PhWarningOctagon,
} from '@phosphor-icons/vue';

// Types
import { CustomDomain, DNSRecord, StaleDNSRecord, STEP, DOMAIN_STATUS, DNSRecordStatus } from '../types';
import type {
  DomainVerificationResult,
  InlineIssueSeverity,
  InlineIssue,
  DnsTableRow,
  DecoratedDnsTableRow,
  RowAction,
  RowStatus,
} from '../types';

// API
import { addCustomDomain, verifyDomain, getRemoteDNSRecords } from '../api';

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
const copiedCellKey = ref<string | null>(null);
let copiedResetTimer: ReturnType<typeof setTimeout> | undefined;

const copyCellValue = async (cellKey: string, value: string) => {
  try {
    await navigator.clipboard.writeText(value);
    copiedCellKey.value = cellKey;
    clearTimeout(copiedResetTimer);
    copiedResetTimer = setTimeout(() => {
      copiedCellKey.value = null;
    }, 1500);
  } catch (error) {
    console.error(error);
  }
};

const hasCopyableValue = (value?: string | null): boolean => Boolean(value) && value !== '-';

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

const shouldAnchorDkimMissingIssue = (record: DNSRecord): boolean =>
  showMissingIssues.value &&
  validationWarnings.value.includes('dkimRecordNotFound') &&
  isDkimRecordForCurrentDomain(record);

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
      severity: 'warning',
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
      severity: 'warning',
      text: t('views.mail.sections.customDomains.recordConflictWarning', { currentValue: currentValue(record) }),
    };
  }

  if (record.status === DNSRecordStatus.MISSING) {
    if (!showMissingIssues.value) {
      return null;
    }

    return {
      key: missingKey ?? `${record.type}-${record.name}-missing`,
      severity: 'warning',
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
    severity: 'warning',
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
  staleDnsRecords.value.filter((record) => record.code === 'autodiscoverCnameUnexpected').map(createStaleDnsTableRow)
);

const staleSrvRows = computed(() =>
  staleDnsRecords.value.filter((record) => record.code === 'autodiscoverSrvUnexpected').map(createStaleDnsTableRow)
);

const rowAction = (row: DnsTableRow): RowAction | null => {
  if (row.isStale || row.isConflict) {
    return 'remove';
  }

  switch (row.record.status) {
    case DNSRecordStatus.MISSING:
      return 'add';
    case DNSRecordStatus.CONFLICT:
      return 'edit';
    case DNSRecordStatus.UNKNOWN:
      return row.issues.length > 0 ? 'add' : null;
    default:
      return null;
  }
};

const rowStatus = (row: DnsTableRow, action: RowAction | null): RowStatus => {
  if (row.severity === 'warning' || action) {
    return 'warning';
  }
  return 'success';
};

const decorateRow = (row: DnsTableRow): DecoratedDnsTableRow => {
  const action = rowAction(row);
  return { ...row, action, status: rowStatus(row, action) };
};

const dnsTableRows = computed<DecoratedDnsTableRow[]>(() => {
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

  return rows.map(decorateRow);
});

const actionLabel = (action: RowAction): string => t(`views.mail.sections.customDomains.recordAction.${action}`);

const issuesTooltip = (issues: InlineIssue[]): string => issues.map((issue) => issue.text).join('\n');

const anchoredValidationKeys = computed(
  () => new Set(dnsTableRows.value.flatMap((row) => row.issues.map((issue) => issue.key)))
);

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

      <notice-bar
        :type="NoticeBarTypes.Critical"
        v-if="domainAlreadyConfigured"
        class="domain-already-configured-notice-bar"
      >
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
      <div class="records-table">
        <div class="records-table-header">
          <p class="records-cell-status" aria-hidden="true"></p>
          <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderType') }}</p>
          <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderNameHost') }}</p>
          <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderValueData') }}</p>
          <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderPriority') }}</p>
          <p class="records-cell-action" aria-hidden="true"></p>
        </div>
        <div
          class="records-table-row"
          :class="{
            'record-warning': row.severity === 'warning',
            'record-stale': row.isStale,
            'record-conflict': row.isConflict,
          }"
          v-for="row in dnsTableRows"
          :key="row.key"
        >
          <div class="records-cell records-cell-status">
            <ph-check-circle
              v-if="row.status === 'success'"
              size="16"
              weight="duotone"
              class="status-icon status-icon-success"
              aria-hidden="true"
            />
            <ph-warning v-else size="16" weight="duotone" class="status-icon status-icon-warning" aria-hidden="true" />
          </div>

          <p class="records-cell">{{ row.record.type }}</p>

          <div class="records-cell records-cell-copyable">
            <span>{{ row.record.name }}</span>
            <button
              v-if="hasCopyableValue(row.record.name)"
              type="button"
              class="copy-button"
              :aria-label="t('views.mail.sections.customDomains.copyValue')"
              @click="copyCellValue(`${row.key}-name`, row.record.name)"
            >
              <ph-check v-if="copiedCellKey === `${row.key}-name`" size="14" />
              <ph-copy-simple v-else size="14" />
            </button>
          </div>

          <div class="records-cell records-cell-copyable">
            <span>{{ row.record.content }}</span>
            <button
              v-if="hasCopyableValue(row.record.content)"
              type="button"
              class="copy-button"
              :aria-label="t('views.mail.sections.customDomains.copyValue')"
              @click="copyCellValue(`${row.key}-content`, row.record.content)"
            >
              <ph-check v-if="copiedCellKey === `${row.key}-content`" size="14" />
              <ph-copy-simple v-else size="14" />
            </button>
          </div>

          <div class="records-cell records-cell-copyable">
            <span>{{ row.record.priority || '-' }}</span>
            <button
              v-if="hasCopyableValue(row.record.priority)"
              type="button"
              class="copy-button"
              :aria-label="t('views.mail.sections.customDomains.copyValue')"
              @click="copyCellValue(`${row.key}-priority`, row.record.priority || '')"
            >
              <ph-check v-if="copiedCellKey === `${row.key}-priority`" size="14" />
              <ph-copy-simple v-else size="14" />
            </button>
          </div>

          <div class="records-cell records-cell-action">
            <span v-if="row.action" class="action-badge" :class="`action-badge-${row.action}`">
              {{ actionLabel(row.action) }}
            </span>
            <ph-info
              v-if="row.issues.length > 0"
              size="18"
              class="action-info-icon"
              :class="`action-info-icon-${row.severity}`"
              :title="issuesTooltip(row.issues)"
            />
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

    <primary-button class="verify-step-button" @click="onVerifyDomain" :disabled="isVerifyingDomain">
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
  }

  .verify-step-note {
    font-size: 0.875rem;
    line-height: normal;
    margin: 0;
  }
}

.records-table-wrapper {
  --records-grid-columns: 3rem max-content minmax(150px, 1fr) minmax(200px, 1fr) max-content max-content;

  overflow-x: auto;
  margin-block-end: 1.5rem;
}

.records-table {
  display: grid;
  grid-template-columns: var(--records-grid-columns);
  min-width: max-content;
}

.records-table-header,
.records-table-row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
}

.records-table-header {
  border-block-end: 1px solid var(--colour-neutral-border);

  p {
    padding: 1rem;
    text-transform: uppercase;
    font-weight: 600;
    font-size: 0.8125rem;
    letter-spacing: 0.39px;
  }
}

.records-table-row {
  border-block-end: 0.0625rem solid var(--colour-neutral-border);

  &.record-warning {
    border-block-end-color: var(--colour-warning-default);
    background-color: var(--colour-warning-soft);
  }
}

.records-cell {
  padding: 1rem;
  margin: 0;
  font-size: 0.75rem;
  word-break: break-word;
}

.records-cell-status {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-inline: 0;
}

.status-icon {
  flex: 0 0 auto;
}

.status-icon-success {
  color: var(--colour-success-pressed);
}

.status-icon-warning {
  color: var(--colour-ti-warning);
}

.records-cell-copyable {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;

  span {
    word-break: break-word;
  }
}

.copy-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  padding: 0.25rem;
  border: none;
  background: none;
  color: var(--colour-ti-secondary);
  cursor: pointer;

  &:hover {
    color: var(--colour-primary-hover);
  }

  &:active {
    color: var(--colour-primary-pressed);
  }
}

.records-cell-action {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

.action-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border: 1px solid currentColor;
  border-radius: 300px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.39px;
  white-space: nowrap;
}

.action-badge-add {
  color: var(--colour-ti-success);
}

.action-badge-edit {
  color: var(--colour-ti-warning);
}

.action-badge-remove {
  color: var(--colour-danger-default);
}

.action-info-icon {
  flex: 0 0 auto;
  color: var(--colour-ti-secondary);
  cursor: help;
}

.action-info-icon-critical {
  color: var(--colour-danger-default);
}

.action-info-icon-warning {
  color: var(--colour-ti-warning);
}

.records-table-footer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1rem 1rem;
}

.records-table-footer {
  grid-column: 1 / -1;
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

  .records-table {
    min-width: auto;
  }
}
</style>
