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
  priority?: number;
}
