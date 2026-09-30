export enum EMAIL_ALIAS_STEP {
  INITIAL = 'initial',
  SUBMIT = 'submit',
}

export interface EmailAlias {
  email: string;
  domain: string;
  isPrimary?: boolean;
  isSubscription?: boolean;
  isCatchAll: boolean;
}
