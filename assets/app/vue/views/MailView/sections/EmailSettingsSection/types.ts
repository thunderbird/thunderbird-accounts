export enum EMAIL_ALIAS_STEP {
  INITIAL = 'initial',
  SUBMIT = 'submit',
}

export interface EmailAlias {
  id: number;
  email: string;
  isPrimary?: boolean;
  isSubscription?: boolean;
}
