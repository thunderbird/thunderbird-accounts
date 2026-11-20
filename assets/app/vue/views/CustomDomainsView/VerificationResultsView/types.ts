export type ApiDnsRecord = {
  type: string;
  name: string;
  content: string;
  priority?: string;
  status?: 'match' | 'conflict' | 'missing' | 'unknown';
  existing_values?: string[];
};

export type ApiStaleDnsRecord = {
  code: string;
  type: string;
  name: string;
  existing_values: string[];
};

// Shape returned by the verify endpoint
export type VerificationApiResult = {
  success?: boolean;
  code?: string;
  critical_errors?: string[];
  warnings?: string[];
  dns_records?: ApiDnsRecord[];
  stale_dns_records?: ApiStaleDnsRecord[];
};
