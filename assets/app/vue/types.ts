/* Source: https://docs.djangoproject.com/en/5.2/ref/contrib/messages/#creating-custom-message-levels */
export enum SERVER_MESSAGE_LEVEL {
  DEBUG = 10,
  INFO = 20,
  SUCCESS = 25,
  WARNING = 30,
  ERROR = 40,
};

export type ServerMessage = {
  level: SERVER_MESSAGE_LEVEL;
  message: string;
};

export enum FeatureFlag {
  SHOW_CONNECT_NOW = 'feature.show-connect-now',
  SHOW_MFA = 'feature.show-mfa',
};

export enum FeatureFlagValue {
  TRUE = 'true',
};

export enum TELEMETRY_EVENTS {
  SIGN_UP_SUPPORT = 'accounts.sign-up.support', 
  SIGN_UP_ERROR = 'accounts.sign-up.error',
  SIGN_UP_STEP = 'accounts.sign-up.step',
};

// Linked with thunderbird_accounts.authentication.api.CanISignUpResponses
export enum CAN_I_SIGN_UP_RESPONSES { 
  WAIT_LIST = 'wait-list',
  LOGIN = 'login',
  SIGN_UP = 'sign-up'
};
