export enum DOMAIN_STATUS {
  VERIFIED = 'verified',
  PENDING = 'pending',
  FAILED = 'failed',
};

export enum STEP {
  INITIAL = 'initial',
  ADD = 'add',
  VERIFY_DOMAIN = 'verify',
};

export enum DNSRecordStatus {
  MATCH = 'match',
  CONFLICT = 'conflict',
  MISSING = 'missing',
  UNKNOWN = 'unknown',
};

export type DNSRecord = {
  type: string;
  name: string;
  content: string;
  priority?: string;
  status?: DNSRecordStatus;
  existing_values?: string[];
};

export type StaleDNSRecord = {
  code: string;
  type: string;
  name: string;
  existing_values: string[];
};

export type CustomDomain = {
  name: string;
  status: DOMAIN_STATUS;
  emailsCount?: number;
};

export type DomainVerificationResult = {
  domainName: string;
  dnsRecords: DNSRecord[];
  staleDnsRecords: StaleDNSRecord[];
  criticalErrors: string[];
  warnings: string[];
};

export type InlineIssueSeverity = 'critical' | 'warning';

export type RowAction = 'add' | 'edit' | 'remove';

export type RowStatus = 'success' | 'warning' | 'critical';

export type InlineIssue = {
  key: string;
  severity: InlineIssueSeverity;
  text: string;
};

export type DnsTableRow = {
  key: string;
  record: DNSRecord;
  issues: InlineIssue[];
  severity: InlineIssueSeverity | null;
  isStale: boolean;
  isConflict: boolean;
};

export type DecoratedDnsTableRow = DnsTableRow & {
  action: RowAction | null;
  status: RowStatus;
};

export enum RecordTab {
  CONFLICTING = 'conflicting',
  ALL = 'all',
}
