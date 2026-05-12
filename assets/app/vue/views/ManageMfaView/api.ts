export interface TotpCredential {
  id: string;
  label: string;
  createdDate?: number;
  lastUsedDate?: number;
}

export interface RecoveryCodesCredential {
  id: string;
  label: string;
  createdDate?: number;
  lastUsedDate?: number;
  totalCodes?: number;
  remainingCodes?: number;
}

export interface MfaMethodsResponse {
  success: boolean;
  error?: string;
  methods: {
    authenticatorApp: {
      set: boolean;
      credentials: TotpCredential[];
    };
    recoveryCodes: {
      set: boolean;
      credentials: RecoveryCodesCredential[];
    };
  };
}

export interface RecoveryCodesSetupStartResponse {
  success: boolean;
  error?: string;
  codes: string[];
}

export interface RecoveryCodesSetupConfirmResponse {
  success: boolean;
  error?: string;
  credentials: RecoveryCodesCredential[];
}

export interface TotpSetupResponse {
  success: boolean;
  error?: string;
  secret: string;
  otpAuthUri: string;
  issuer: string;
  accountName: string;
  digits: number;
  period: number;
  algorithm: string;
}

export interface TotpConfirmResponse {
  success: boolean;
  error?: string;
  credentials: TotpCredential[];
}

export class MfaReauthenticationRequiredError extends Error {
  reauthUrl: string;

  constructor(message: string, reauthUrl: string) {
    super(message);
    this.name = 'MfaReauthenticationRequiredError';
    this.reauthUrl = reauthUrl;
  }
}

const jsonHeaders = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
  'X-CSRFToken': window._page?.csrfToken,
};

const parseJsonResponse = async <T>(response: Response): Promise<T> => {
  const data = await response.json();

  if (response.status === 403 && data.reauthUrl) {
    throw new MfaReauthenticationRequiredError(data.error || response.statusText, data.reauthUrl);
  }

  if (!response.ok || data.success === false) {
    throw new Error(data.error || response.statusText);
  }

  return data;
};

export const getMfaMethods = async () => {
  const response = await fetch('/api/v1/auth/mfa/methods/', {
    method: 'GET',
    headers: jsonHeaders,
  });

  return parseJsonResponse<MfaMethodsResponse>(response);
};

export const startTotpSetup = async () => {
  const response = await fetch('/api/v1/auth/mfa/totp/setup/start/', {
    method: 'POST',
    headers: jsonHeaders,
  });

  return parseJsonResponse<TotpSetupResponse>(response);
};

export const confirmTotpSetup = async (code: string, logoutOtherSessions: boolean) => {
  const response = await fetch('/api/v1/auth/mfa/totp/setup/confirm/', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ code, logoutOtherSessions }),
  });

  return parseJsonResponse<TotpConfirmResponse>(response);
};

export const removeTotpCredential = async (credentialId: string) => {
  const response = await fetch(`/api/v1/auth/mfa/totp/credentials/${credentialId}/`, {
    method: 'DELETE',
    headers: jsonHeaders,
  });

  return parseJsonResponse<{ success: boolean }>(response);
};

export const startRecoveryCodesSetup = async () => {
  const response = await fetch('/api/v1/auth/mfa/recovery-codes/setup/start/', {
    method: 'POST',
    headers: jsonHeaders,
  });

  return parseJsonResponse<RecoveryCodesSetupStartResponse>(response);
};

export const confirmRecoveryCodesSetup = async () => {
  const response = await fetch('/api/v1/auth/mfa/recovery-codes/setup/confirm/', {
    method: 'POST',
    headers: jsonHeaders,
  });

  return parseJsonResponse<RecoveryCodesSetupConfirmResponse>(response);
};

export const removeRecoveryCodesCredential = async (credentialId: string) => {
  const response = await fetch(`/api/v1/auth/mfa/recovery-codes/credentials/${credentialId}/`, {
    method: 'DELETE',
    headers: jsonHeaders,
  });

  return parseJsonResponse<{ success: boolean }>(response);
};
