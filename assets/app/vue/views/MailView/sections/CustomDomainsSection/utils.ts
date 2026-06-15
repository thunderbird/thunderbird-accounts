import {
  DNSRecordStatus,
  type DNSRecord,
  type DecoratedDnsTableRow,
  type DnsTableRow,
  type DomainVerificationResult,
  type InlineIssue,
  type InlineIssueSeverity,
  type RowAction,
  type RowStatus,
  type StaleDNSRecord,
} from './types';

export const hasCopyableValue = (value?: string | null): boolean => Boolean(value) && value !== '-';

export const isMxRecord = (record: DNSRecord): boolean => record.type === 'MX';

export const isSpfRecord = (record: DNSRecord): boolean =>
  record.type === 'TXT' && record.content.trim().toLowerCase().startsWith('v=spf1');

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

export const isDkimRecordForCurrentDomain = (record: DNSRecord, customDomain: string): boolean =>
  dkimRecordDomain(record) === normalizeDomainName(customDomain);

export const recordValidationKeys = (record: DNSRecord, customDomain: string): string[] => {
  const keys = [];
  if (isMxRecord(record)) {
    keys.push('mxLookupError');
  }
  if (isSpfRecord(record)) {
    keys.push('spfRecordNotFound');
  }
  if (isDkimRecordForCurrentDomain(record, customDomain)) {
    keys.push('dkimRecordNotFound');
  }
  return keys;
};

export const MISSING_VALIDATION_KEYS = new Set(['mxLookupError', 'spfRecordNotFound', 'dkimRecordNotFound']);

export const missingOrConflicted = (record: DNSRecord): boolean =>
  record.status === DNSRecordStatus.MISSING || record.status === DNSRecordStatus.CONFLICT;

export const hasValidationIssue = (
  key: string,
  criticalErrors: string[],
  validationWarnings: string[]
): boolean => criticalErrors.includes(key) || validationWarnings.includes(key);

export const validationSeverity = (
  key: string | null | undefined,
  criticalErrors: string[]
): InlineIssueSeverity => (key && criticalErrors.includes(key) ? 'critical' : 'warning');

export const shouldAnchorDkimMissingIssue = (
  record: DNSRecord,
  customDomain: string,
  showMissingIssues: boolean,
  criticalErrors: string[],
  validationWarnings: string[]
): boolean =>
  showMissingIssues &&
  hasValidationIssue('dkimRecordNotFound', criticalErrors, validationWarnings) &&
  isDkimRecordForCurrentDomain(record, customDomain);

export const conflictSeverity = (
  record: DNSRecord,
  customDomain: string,
  criticalErrors: string[]
): InlineIssueSeverity =>
  isMxRecord(record) ||
  recordValidationKeys(record, customDomain).some((key) => criticalErrors.includes(key))
    ? 'critical'
    : 'warning';

export type DnsTableI18n = {
  t: (key: string, params?: Record<string, unknown>) => string;
  te: (key: string) => boolean;
};

export type DnsTableState = {
  customDomain: string;
  criticalErrors: string[];
  validationWarnings: string[];
  showMissingIssues: boolean;
};

export const formatValidationError = (error: string, { t, te }: DnsTableI18n): string => {
  const translationKey = `views.mail.sections.customDomains.verificationValidationErrors.${error}`;
  return te(translationKey) ? t(translationKey) : error;
};

export const validationResultFromApi = (data?: {
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

export const issueSeverity = (issues: InlineIssue[]): InlineIssueSeverity | null => {
  if (issues.some((issue) => issue.severity === 'critical')) {
    return 'critical';
  }
  if (issues.length > 0) {
    return 'warning';
  }
  return null;
};

export const recordStatusIssue = (
  record: DNSRecord,
  state: DnsTableState,
  i18n: DnsTableI18n
): InlineIssue | null => {
  const { customDomain, criticalErrors, validationWarnings, showMissingIssues } = state;
  const { t } = i18n;
  const validationKeys = recordValidationKeys(record, customDomain);
  const validationKey = validationKeys.find(
    (key) => criticalErrors.includes(key) || validationWarnings.includes(key)
  );
  const missingKey = validationKey ?? validationKeys.find((key) => MISSING_VALIDATION_KEYS.has(key));

  if (isMxRecord(record) && record.status === DNSRecordStatus.CONFLICT) {
    return {
      key: 'mxLookupError',
      severity: 'critical',
      text: t('views.mail.sections.customDomains.mxRecordConflictWarning'),
    };
  }

  if (isMxRecord(record) && record.status === DNSRecordStatus.MISSING) {
    if (!showMissingIssues) {
      return null;
    }

    return {
      key: 'mxLookupError',
      severity: 'critical',
      text: formatValidationError('mxLookupError', i18n),
    };
  }

  if (
    record.status === DNSRecordStatus.UNKNOWN &&
    shouldAnchorDkimMissingIssue(record, customDomain, showMissingIssues, criticalErrors, validationWarnings)
  ) {
    return {
      key: 'dkimRecordNotFound',
      severity: validationSeverity('dkimRecordNotFound', criticalErrors),
      text: t('views.mail.sections.customDomains.recordMissingWarning'),
    };
  }

  if (isSpfRecord(record) && record.status === DNSRecordStatus.CONFLICT) {
    const includeValue =
      record.content.split(/\s+/).find((part) => part.startsWith('include:')) ??
      t('views.mail.sections.customDomains.spfRecordIncludeValue');

    return {
      key: 'spfRecordNotFound',
      severity: 'warning',
      text: t('views.mail.sections.customDomains.spfRecordConflictWarning', { includeValue }),
    };
  }

  if (record.status === DNSRecordStatus.CONFLICT) {
    return {
      key: validationKey ?? `${record.type}-${record.name}-conflict`,
      severity: validationSeverity(validationKey, criticalErrors),
      text: t('views.mail.sections.customDomains.recordConflictWarning', {
        currentValue: record.existing_values?.join(', ') || '-',
      }),
    };
  }

  if (record.status === DNSRecordStatus.MISSING) {
    if (!showMissingIssues) {
      return null;
    }

    return {
      key: missingKey ?? `${record.type}-${record.name}-missing`,
      severity: validationSeverity(missingKey, criticalErrors),
      text: t('views.mail.sections.customDomains.recordMissingWarning'),
    };
  }

  return null;
};

export const validationIssuesForRecord = (
  record: DNSRecord,
  state: DnsTableState,
  i18n: DnsTableI18n
): InlineIssue[] => {
  const { customDomain, criticalErrors, validationWarnings, showMissingIssues } = state;

  return recordValidationKeys(record, customDomain)
    .filter((key) => criticalErrors.includes(key) || validationWarnings.includes(key))
    .filter((key) => showMissingIssues || !MISSING_VALIDATION_KEYS.has(key))
    .filter((key) => key === 'mxLookupError' || missingOrConflicted(record))
    .map((key) => ({
      key,
      severity: criticalErrors.includes(key) ? ('critical' as const) : ('warning' as const),
      text: formatValidationError(key, i18n),
    }));
};

export const createConflictingRecord = (record: DNSRecord, existingValue: string): DNSRecord => {
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

export const createDnsTableRow = (
  record: DNSRecord,
  index: number,
  state: DnsTableState,
  i18n: DnsTableI18n
): DnsTableRow => {
  const hasConflictRows = record.status === DNSRecordStatus.CONFLICT && (record.existing_values?.length ?? 0) > 0;
  const statusIssue = hasConflictRows ? null : recordStatusIssue(record, state, i18n);
  const validationIssues = statusIssue || hasConflictRows ? [] : validationIssuesForRecord(record, state, i18n);
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

export const createConflictDnsTableRows = (
  record: DNSRecord,
  index: number,
  state: DnsTableState,
  i18n: DnsTableI18n
): DnsTableRow[] => {
  if (record.status !== DNSRecordStatus.CONFLICT || !record.existing_values?.length) {
    return [];
  }

  const statusIssue = recordStatusIssue(record, state, i18n);
  const validationIssues = statusIssue ? [] : validationIssuesForRecord(record, state, i18n);
  const issues = statusIssue ? [statusIssue, ...validationIssues] : validationIssues;

  return record.existing_values.map((existingValue, conflictIndex) => ({
    key: `conflict-${record.type}-${record.name}-${existingValue}-${index}-${conflictIndex}`,
    record: createConflictingRecord(record, existingValue),
    issues: conflictIndex === 0 ? issues : [],
    severity: conflictSeverity(record, state.customDomain, state.criticalErrors),
    isStale: false,
    isConflict: true,
  }));
};

export const createDnsTableRows = (
  record: DNSRecord,
  index: number,
  state: DnsTableState,
  i18n: DnsTableI18n
): DnsTableRow[] => [
  createDnsTableRow(record, index, state, i18n),
  ...createConflictDnsTableRows(record, index, state, i18n),
];

export const createStaleDnsTableRow = (
  record: StaleDNSRecord,
  i18n: DnsTableI18n
): DnsTableRow => {
  const isSrv = record.code === 'autodiscoverSrvUnexpected';
  const validationKey = isSrv ? 'autodiscoverSrvRecordFound' : 'autodiscoverRecordFound';
  const issues = [
    {
      key: validationKey,
      severity: 'critical' as const,
      text: formatValidationError(validationKey, i18n),
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

export const rowAction = (row: DnsTableRow): RowAction | null => {
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

export const rowStatus = (row: DnsTableRow, action: RowAction | null): RowStatus => {
  if (row.severity === 'warning' || action) {
    return 'warning';
  }
  return 'success';
};

export const decorateDnsTableRow = (row: DnsTableRow): DecoratedDnsTableRow => {
  const action = rowAction(row);
  return { ...row, action, status: rowStatus(row, action) };
};

export const buildDecoratedDnsTableRows = (
  recordsInfo: DNSRecord[],
  staleDnsRecords: StaleDNSRecord[],
  state: DnsTableState,
  i18n: DnsTableI18n
): DecoratedDnsTableRow[] => {
  const staleAddressRows = staleDnsRecords
    .filter((record) => record.code === 'autodiscoverCnameUnexpected')
    .map((record) => createStaleDnsTableRow(record, i18n));
  const staleSrvRows = staleDnsRecords
    .filter((record) => record.code === 'autodiscoverSrvUnexpected')
    .map((record) => createStaleDnsTableRow(record, i18n));

  const expectedRows = recordsInfo.flatMap((record, index) => createDnsTableRows(record, index, state, i18n));
  const rows: DnsTableRow[] = [];
  let insertedAddressRows = false;
  let insertedSrvRows = false;

  expectedRows.forEach((row, index) => {
    rows.push(row);
    const nextRow = expectedRows[index + 1];

    if (!insertedSrvRows && row.record.type === 'SRV' && nextRow?.record.type !== 'SRV') {
      rows.push(...staleSrvRows);
      insertedSrvRows = true;
    }

    if (!insertedAddressRows && row.record.type === 'CNAME' && nextRow?.record.type !== 'CNAME') {
      rows.push(...staleAddressRows);
      insertedAddressRows = true;
    }
  });

  if (!insertedSrvRows) {
    rows.push(...staleSrvRows);
  }
  if (!insertedAddressRows) {
    rows.push(...staleAddressRows);
  }

  return rows.map(decorateDnsTableRow);
};

export const buildUnanchoredValidationIssues = (
  criticalErrors: string[],
  validationWarnings: string[],
  anchoredValidationKeys: Set<string>,
  showMissingIssues: boolean,
  i18n: DnsTableI18n
): InlineIssue[] => [
  ...criticalErrors
    .filter((key) => !anchoredValidationKeys.has(key))
    .filter((key) => showMissingIssues || !MISSING_VALIDATION_KEYS.has(key))
    .map((key) => ({
      key,
      severity: 'critical' as const,
      text: formatValidationError(key, i18n),
    })),
  ...validationWarnings
    .filter((key) => !anchoredValidationKeys.has(key))
    .filter((key) => showMissingIssues || !MISSING_VALIDATION_KEYS.has(key))
    .map((key) => ({
      key,
      severity: 'warning' as const,
      text: formatValidationError(key, i18n),
    })),
];
