import { DNS_RECORD_STATUS } from '../types';
import type { DNSRecord } from '../types';
import type { ApiDnsRecord, VerificationApiResult } from './types';

type Translate = (key: string, params?: Record<string, unknown>) => string;

const MESSAGES = 'views.mail.sections.customDomains';

const isSpfRecord = (record: ApiDnsRecord): boolean =>
  record.type === 'TXT' && record.content.trim().toLowerCase().startsWith('v=spf1');

const conflictMessage = (record: ApiDnsRecord, existingValue: string, t: Translate): string => {
  if (record.type === 'MX') {
    return t(`${MESSAGES}.mxRecordConflictWarning`);
  }
  if (record.type === 'SRV') {
    return t(`${MESSAGES}.srvRecordConflictWarning`);
  }
  if (isSpfRecord(record)) {
    const includeValue = record.content.split(/\s+/).find((part) => part.startsWith('include:'));
    return t(`${MESSAGES}.spfRecordConflictWarning`, { includeValue: includeValue ?? '' });
  }
  return t(`${MESSAGES}.recordConflictWarning`, { currentValue: existingValue });
};

// A conflicting record only reports what is currently set, e.g. "10 mail.example.com" for an MX record
const toExistingRecord = (record: ApiDnsRecord, existingValue: string): Pick<DNSRecord, 'content' | 'priority'> => {
  const parts = existingValue.trim().split(/\s+/);
  const hasPriority = (record.type === 'MX' && parts.length > 1) || (record.type === 'SRV' && parts.length > 3);

  return hasPriority
    ? { content: parts.slice(1).join(' '), priority: parts[0] }
    : { content: existingValue, priority: '-' };
};

export const buildResultRecords = (result: VerificationApiResult, t: Translate): DNSRecord[] => {
  const rows: DNSRecord[] = [];

  (result.dns_records ?? []).forEach((record) => {
    const expected: DNSRecord = {
      type: record.type,
      name: record.name,
      content: record.content,
      priority: record.priority,
    };

    switch (record.status) {
      case 'match':
        rows.push({ ...expected, status: DNS_RECORD_STATUS.VERIFIED });
        break;
      case 'missing':
        rows.push({
          ...expected,
          status: DNS_RECORD_STATUS.NOT_FOUND,
          issue: t('views.customDomains.verificationResults.recordNotFound', { type: record.type, name: record.name }),
        });
        break;
      case 'conflict': {
        const existingValues = record.existing_values ?? [];
        if (existingValues.length === 0) {
          rows.push({
            ...expected,
            status: DNS_RECORD_STATUS.ACTION_REQUIRED,
            issue: conflictMessage(record, '-', t),
          });
          break;
        }

        // The required record first, followed by what is currently set that needs replacing
        rows.push(expected);
        existingValues.forEach((existingValue) => {
          rows.push({
            type: record.type,
            name: record.name,
            ...toExistingRecord(record, existingValue),
            status: DNS_RECORD_STATUS.ACTION_REQUIRED,
            issue: conflictMessage(record, existingValue, t),
          });
        });
        break;
      }
      default:
        rows.push(expected);
    }
  });

  (result.stale_dns_records ?? []).forEach((record) => {
    const messageKey = record.code === 'autodiscoverSrvUnexpected'
      ? 'autodiscoverSrvRecordFound'
      : 'autodiscoverRecordFound';

    rows.push({
      type: record.type,
      name: record.name,
      content: record.existing_values.join(', '),
      priority: '-',
      status: DNS_RECORD_STATUS.ACTION_REQUIRED,
      issue: t(`${MESSAGES}.verificationValidationErrors.${messageKey}`),
    });
  });

  return rows;
};
