export enum DNS_RECORD_STATUS {
  VERIFIED = 'verified',
  ACTION_REQUIRED = 'action-required',
  NOT_FOUND = 'not-found',
}

export type DNSRecord = {
  type: string;
  name: string;
  content: string;
  priority?: string;
  // Only set once a record has been through verification
  status?: DNS_RECORD_STATUS;
  // Explains what to do about a record that needs attention
  issue?: string;
};

export type DnsProviderField = {
  label: string;
  // May contain {tokens} such as {host} or {priority}, and a trailing hint after two or more spaces
  template: string;
};

export type DnsProviderRecordInstructions = {
  fields: DnsProviderField[];
};

export type DnsProviderConfig = {
  id: string;
  label: string;
  records: Record<'MX' | 'SRV' | 'TXT' | 'CNAME', DnsProviderRecordInstructions>;
};

export type TokenContext = Record<string, string>;

export type ProviderCell = {
  label: string;
  // What belongs in the provider's field, empty when it should be left blank
  value: string;
  hint: string;
};

export type ProviderRecordGroup = {
  type: string;
  columns: string[];
  rows: ProviderCell[][];
};
