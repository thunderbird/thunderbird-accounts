export enum DOMAIN_STATUS {
  VERIFIED = 'verified',
  PENDING = 'pending',
  FAILED = 'failed',
}

export enum STEP {
  INITIAL = 'initial',
  ADD = 'add',
  VERIFY_DOMAIN = 'verify',
}

export type DNSRecord = {
  type: string;
  name: string;
  content: string;
  priority?: string;
}

export type CustomDomain = {
  name: string;
  status: DOMAIN_STATUS;
  emailsCount?: number;
}

export type CustomDomain = {
  name: string;
  status: DOMAIN_STATUS;
  emailsCount?: number;
}
