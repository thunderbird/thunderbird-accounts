import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  getMfaMethods,
  RecoveryCodesCredential,
  removeRecoveryCodesCredential,
  removeTotpCredential,
  TotpCredential,
} from './api';
import { MANAGE_MFA_FEATURES } from './features';
import { useMfaAction } from './useMfaAction';

export enum AUTHENTICATION_METHODS {
  AUTHENTICATOR_APP = 'authenticatorApp',
  RECOVERY_CODES = 'recoveryCodes',
  RECOVERY_PHONE_NUMBER = 'recoveryPhoneNumber',
  RECOVERY_EMAIL_ADDRESS = 'recoveryEmailAddress',
}

export interface AuthenticationMethodData {
  set: boolean;
  setupDate?: string;
  lastUsedDate?: string;
  credentials?: Array<TotpCredential | RecoveryCodesCredential>;
  remainingCodes?: number;
  totalCodes?: number;
}

interface MfaMethodsOptions {
  /** Open the OIDC step-up ("verify your identity") modal. */
  openVerifyModal: () => void;
  /** Open the recovery-codes modal (used to auto-chain after first TOTP setup). */
  openRecoveryCodesModal: () => void;
  /** Open the shared "remove method" confirmation modal. */
  openRemoveModal: () => void;
  /** Close the shared "remove method" confirmation modal. */
  closeRemoveModal: () => void;
}

const featureEnabledFor = (method: string): boolean => {
  switch (method) {
    case AUTHENTICATION_METHODS.AUTHENTICATOR_APP:
      return MANAGE_MFA_FEATURES.authenticatorApp;
    case AUTHENTICATION_METHODS.RECOVERY_CODES:
      return MANAGE_MFA_FEATURES.recoveryCodes;
    case AUTHENTICATION_METHODS.RECOVERY_EMAIL_ADDRESS:
      return MANAGE_MFA_FEATURES.recoveryEmail;
    case AUTHENTICATION_METHODS.RECOVERY_PHONE_NUMBER:
      return MANAGE_MFA_FEATURES.recoveryPhone;
    default:
      return false;
  }
};

const formatDate = (date: number) => new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
}).format(date);

/**
 * State and orchestration for the Manage MFA view: loading enrolled methods, mapping
 * Keycloak credentials into view state, the step-up (reauth) handoff, and the
 * remove-credential confirmation flow. Imperative modal opening is delegated back to the
 * component via `options` so the composable stays free of template refs.
 */
export function useMfaMethods(options: MfaMethodsOptions) {
  const { t } = useI18n();
  const { isLoading, errorMessage, run } = useMfaAction();

  const authenticationMethods = ref<Record<AUTHENTICATION_METHODS, AuthenticationMethodData>>({
    [AUTHENTICATION_METHODS.AUTHENTICATOR_APP]: { set: false },
    [AUTHENTICATION_METHODS.RECOVERY_CODES]: { set: false },
    [AUTHENTICATION_METHODS.RECOVERY_PHONE_NUMBER]: { set: false },
    [AUTHENTICATION_METHODS.RECOVERY_EMAIL_ADDRESS]: { set: false },
  });

  const reauthenticationUrl = ref('');
  const isRemoving = ref(false);
  const pendingRemove = ref<{ method: AUTHENTICATION_METHODS; credentialId: string } | null>(null);

  const authenticationMethodEntries = computed(
    () => Object.entries(authenticationMethods.value).filter(([method]) => featureEnabledFor(method)),
  );

  const requestMfaVerification = (reauthUrl: string) => {
    reauthenticationUrl.value = reauthUrl;
    options.openVerifyModal();
  };

  const setAuthenticatorCredentials = (credentials: TotpCredential[]) => {
    // The UI surfaces a single authenticator app today; if/when we expose
    // multiple TOTP credentials, this needs to render each instead of only [0].
    const firstCredential = credentials[0];
    authenticationMethods.value[AUTHENTICATION_METHODS.AUTHENTICATOR_APP] = {
      set: credentials.length > 0,
      setupDate: firstCredential?.createdDate ? formatDate(firstCredential.createdDate) : undefined,
      lastUsedDate: firstCredential?.lastUsedDate ? formatDate(firstCredential.lastUsedDate) : undefined,
      credentials,
    };
  };

  const setRecoveryCodesCredentials = (credentials: RecoveryCodesCredential[]) => {
    // Keycloak only allows one recovery-codes credential per user, so we always
    // render the first (and only) entry.
    const firstCredential = credentials[0];
    authenticationMethods.value[AUTHENTICATION_METHODS.RECOVERY_CODES] = {
      set: credentials.length > 0,
      setupDate: firstCredential?.createdDate ? formatDate(firstCredential.createdDate) : undefined,
      lastUsedDate: firstCredential?.lastUsedDate ? formatDate(firstCredential.lastUsedDate) : undefined,
      credentials,
      totalCodes: firstCredential?.totalCodes,
      remainingCodes: firstCredential?.remainingCodes,
    };
  };

  const handleAuthenticatorConfigured = (credentials: TotpCredential[]) => {
    const wasSetBefore = authenticationMethods.value[AUTHENTICATION_METHODS.AUTHENTICATOR_APP].set;
    setAuthenticatorCredentials(credentials);

    // After the user's first authenticator app is set up, prompt them to also save
    // recovery codes. Only when recovery codes aren't already configured — otherwise
    // re-running setup ("Edit") would prompt resetting codes the user already saved.
    const recoveryCodesAlreadySet = authenticationMethods.value[AUTHENTICATION_METHODS.RECOVERY_CODES].set;
    if (!wasSetBefore && !recoveryCodesAlreadySet && MANAGE_MFA_FEATURES.recoveryCodes) {
      options.openRecoveryCodesModal();
    }
  };

  const loadMfaMethods = async () => {
    const response = await run(() => getMfaMethods(), {
      fallbackErrorKey: 'views.manageMfa.errors.load',
      onReauthRequired: requestMfaVerification,
    });
    if (!response) return;

    setAuthenticatorCredentials(response.methods.authenticatorApp.credentials);
    setRecoveryCodesCredentials(response.methods.recoveryCodes.credentials);
  };

  // Per-method config for the remove flow: which API to call, how to reset state on
  // success, and which i18n error/labels to show.
  const removeHandlers = {
    [AUTHENTICATION_METHODS.AUTHENTICATOR_APP]: {
      api: removeTotpCredential,
      resetCredentials: () => setAuthenticatorCredentials([]),
      errorKey: 'views.manageMfa.errors.remove',
      titleKey: 'views.manageMfa.confirmRemoveAuthenticatorApp',
      descriptionKey: 'views.manageMfa.confirmRemoveAuthenticatorAppDescription',
    },
    [AUTHENTICATION_METHODS.RECOVERY_CODES]: {
      api: removeRecoveryCodesCredential,
      resetCredentials: () => setRecoveryCodesCredentials([]),
      errorKey: 'views.manageMfa.errors.removeRecoveryCodes',
      titleKey: 'views.manageMfa.confirmRemoveRecoveryCodes',
      descriptionKey: 'views.manageMfa.confirmRemoveRecoveryCodesDescription',
    },
  } as const;

  type RemovableMethod = keyof typeof removeHandlers;

  const isRemovableMethod = (method: string): method is RemovableMethod => method in removeHandlers;

  const removeModalTitle = computed(() => {
    const method = pendingRemove.value?.method;
    return method && isRemovableMethod(method) ? t(removeHandlers[method].titleKey) : '';
  });

  const removeModalDescription = computed(() => {
    const method = pendingRemove.value?.method;
    return method && isRemovableMethod(method) ? t(removeHandlers[method].descriptionKey) : '';
  });

  const beginRemove = (method: string, methodData: AuthenticationMethodData) => {
    const credentialId = methodData.credentials?.[0]?.id;
    if (!credentialId || !isRemovableMethod(method)) return;

    pendingRemove.value = { method, credentialId };
    options.openRemoveModal();
  };

  const confirmRemove = async () => {
    if (!pendingRemove.value) return;
    const { method, credentialId } = pendingRemove.value;
    const handler = removeHandlers[method];

    const result = await run(() => handler.api(credentialId), {
      fallbackErrorKey: handler.errorKey,
      onReauthRequired: (reauthUrl) => {
        options.closeRemoveModal();
        requestMfaVerification(reauthUrl);
      },
      loadingRef: isRemoving,
    });
    if (!result) return;

    handler.resetCredentials();
    pendingRemove.value = null;
    options.closeRemoveModal();
  };

  const cancelRemove = () => {
    if (!pendingRemove.value) return;
    options.closeRemoveModal();
    pendingRemove.value = null;
  };

  const clearPendingRemove = () => {
    pendingRemove.value = null;
  };

  return {
    authenticationMethods,
    authenticationMethodEntries,
    isLoading,
    errorMessage,
    reauthenticationUrl,
    isRemoving,
    pendingRemove,
    removeModalTitle,
    removeModalDescription,
    loadMfaMethods,
    setAuthenticatorCredentials,
    setRecoveryCodesCredentials,
    handleAuthenticatorConfigured,
    requestMfaVerification,
    beginRemove,
    confirmRemove,
    cancelRemove,
    clearPendingRemove,
  };
}
