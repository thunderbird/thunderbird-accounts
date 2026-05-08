<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCheckCircle } from '@phosphor-icons/vue';
import { BaseBadge, BaseBadgeTypes, VisualDivider, PrimaryButton, LinkButton } from '@thunderbirdops/services-ui';
import {
  getMfaMethods,
  MfaReauthenticationRequiredError,
  RecoveryCodesCredential,
  removeRecoveryCodesCredential,
  removeTotpCredential,
  TotpCredential,
} from '../api';
import { MANAGE_MFA_FEATURES } from '../features';

// Modals
import GenericModal from '@/components/GenericModal.vue';
import ManageAuthenticatorAppModal from './ManageAuthenticatorAppModal.vue';
import ManageRecoveryCodesModal from './ManageRecoveryCodesModal.vue';
import VerifyYourIdentityModal from './VerifyYourIdentityModal.vue';

const { t } = useI18n();

enum AUTHENTICATION_METHODS {
  AUTHENTICATOR_APP = 'authenticatorApp',
  RECOVERY_CODES = 'recoveryCodes',
  RECOVERY_PHONE_NUMBER = 'recoveryPhoneNumber',
  RECOVERY_EMAIL_ADDRESS = 'recoveryEmailAddress'
}

interface AuthenticationMethodData {
  set: boolean;
  setupDate?: string;
  lastUsedDate?: string;
  credentials?: Array<TotpCredential | RecoveryCodesCredential>;
  remainingCodes?: number;
  totalCodes?: number;
}

const authenticationMethods = ref<Record<AUTHENTICATION_METHODS, AuthenticationMethodData>>({
  [AUTHENTICATION_METHODS.AUTHENTICATOR_APP]: {
    set: false,
  },
  [AUTHENTICATION_METHODS.RECOVERY_CODES]: {
    set: false,
  },
  [AUTHENTICATION_METHODS.RECOVERY_PHONE_NUMBER]: {
    set: false,
  },
  [AUTHENTICATION_METHODS.RECOVERY_EMAIL_ADDRESS]: {
    set: false,
  },
});

const manageAuthenticatorAppModal = useTemplateRef<InstanceType<typeof ManageAuthenticatorAppModal>>('manageAuthenticatorAppModal');
const manageRecoveryCodesModal = useTemplateRef<InstanceType<typeof ManageRecoveryCodesModal>>('manageRecoveryCodesModal');
const verifyYourIdentityModal = useTemplateRef<InstanceType<typeof VerifyYourIdentityModal>>('verifyYourIdentityModal');
const removeAuthenticatorModal = useTemplateRef<InstanceType<typeof GenericModal>>('removeAuthenticatorModal');
const removeRecoveryCodesModal = useTemplateRef<InstanceType<typeof GenericModal>>('removeRecoveryCodesModal');
const errorMessage = ref('');
const isLoading = ref(false);
const isRemoving = ref(false);
const pendingRemove = ref<{ method: AUTHENTICATION_METHODS; credentialId: string } | null>(null);
const reauthenticationUrl = ref('');

const authenticationMethodEntries = computed(() => Object.entries(authenticationMethods.value).filter(([method]) => {
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
}));

const formatDate = (date: number) => new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
}).format(date);

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

const handleAuthenticatorConfigured = (credentials: TotpCredential[]) => {
  const wasSetBefore = authenticationMethods.value[AUTHENTICATION_METHODS.AUTHENTICATOR_APP].set;
  setAuthenticatorCredentials(credentials);

  // After the user's first authenticator app is set up, prompt them to also save
  // recovery codes. Only when recovery codes aren't already configured — otherwise
  // re-running setup ("Edit") would silently invalidate codes the user already saved.
  const recoveryCodesAlreadySet = authenticationMethods.value[AUTHENTICATION_METHODS.RECOVERY_CODES].set;
  if (!wasSetBefore && !recoveryCodesAlreadySet && MANAGE_MFA_FEATURES.recoveryCodes) {
    manageRecoveryCodesModal.value.open();
  }
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

const loadMfaMethods = async () => {
  isLoading.value = true;
  errorMessage.value = '';

  try {
    const response = await getMfaMethods();
    setAuthenticatorCredentials(response.methods.authenticatorApp.credentials);
    setRecoveryCodesCredentials(response.methods.recoveryCodes.credentials);
  } catch (error) {
    if (error instanceof MfaReauthenticationRequiredError) {
      requestMfaVerification(error.reauthUrl);
      return;
    }

    errorMessage.value = error instanceof Error ? error.message : t('views.manageMfa.errors.load');
  } finally {
    isLoading.value = false;
  }
};

const handleSetUp = (method: string) => {
  if (method === AUTHENTICATION_METHODS.AUTHENTICATOR_APP) {
    manageAuthenticatorAppModal.value.open();
  } else if (method === AUTHENTICATION_METHODS.RECOVERY_CODES) {
    manageRecoveryCodesModal.value.open();
  }
};

const handleEdit = (method: string) => {
  switch (method) {
    case AUTHENTICATION_METHODS.AUTHENTICATOR_APP:
      manageAuthenticatorAppModal.value.open();
      break;
    case AUTHENTICATION_METHODS.RECOVERY_CODES:
      manageRecoveryCodesModal.value.open();
      break;
    default:
      break;
  }
}

const requestMfaVerification = (reauthUrl: string) => {
  reauthenticationUrl.value = reauthUrl;
  verifyYourIdentityModal.value.open();
};

const handleAuthenticatorReauthRequired = (reauthUrl: string) => {
  requestMfaVerification(reauthUrl);
};

// One row config per method handles all of "what API to call", "how to reset
// state on success", "which dialog ref to drive", and "which i18n error to show
// on a generic failure" — keeping the confirm/cancel handlers below DRY.
const removeHandlers = {
  [AUTHENTICATION_METHODS.AUTHENTICATOR_APP]: {
    api: removeTotpCredential,
    resetCredentials: () => setAuthenticatorCredentials([]),
    modal: removeAuthenticatorModal,
    errorKey: 'views.manageMfa.errors.remove',
  },
  [AUTHENTICATION_METHODS.RECOVERY_CODES]: {
    api: removeRecoveryCodesCredential,
    resetCredentials: () => setRecoveryCodesCredentials([]),
    modal: removeRecoveryCodesModal,
    errorKey: 'views.manageMfa.errors.removeRecoveryCodes',
  },
} as const;

type RemovableMethod = keyof typeof removeHandlers;

const isRemovableMethod = (method: string): method is RemovableMethod => method in removeHandlers;

const handleRemove = (method: string, methodData: AuthenticationMethodData) => {
  const credentialId = methodData.credentials?.[0]?.id;
  if (!credentialId || !isRemovableMethod(method)) return;

  pendingRemove.value = { method, credentialId };
  removeHandlers[method].modal.value.open();
};

const confirmRemove = async () => {
  if (!pendingRemove.value || isRemoving.value) return;
  const { method, credentialId } = pendingRemove.value;
  const handler = removeHandlers[method];

  isRemoving.value = true;
  try {
    await handler.api(credentialId);
    handler.resetCredentials();
    pendingRemove.value = null;
    handler.modal.value.close();
  } catch (error) {
    if (error instanceof MfaReauthenticationRequiredError) {
      handler.modal.value.close();
      requestMfaVerification(error.reauthUrl);
      return;
    }

    errorMessage.value = error instanceof Error ? error.message : t(handler.errorKey);
  } finally {
    isRemoving.value = false;
  }
};

const cancelRemove = () => {
  if (!pendingRemove.value) return;
  removeHandlers[pendingRemove.value.method].modal.value.close();
  pendingRemove.value = null;
};

onMounted(loadMfaMethods);
</script>

<template>
  <div class="authentication-methods-container">
    <header>{{ t('views.manageMfa.authenticationMethods') }}</header>

    <div class="authentication-methods-content">
      <p class="error-message" v-if="errorMessage">{{ errorMessage }}</p>
      <p v-if="isLoading">{{ t('views.manageMfa.loading') }}</p>

      <template v-for="([method, methodData], index) in authenticationMethodEntries" :key="method">
        <div class="authentication-method">
          <div class="authentication-method-content">
            <div class="authentication-method-header">
              <h3>{{ t(`views.manageMfa.${method}.title`) }}</h3>
    
              <base-badge :type="methodData.set ? BaseBadgeTypes.Set : BaseBadgeTypes.NotSet">
                {{ methodData.set ? t('views.manageMfa.states.set') : t('views.manageMfa.states.notSet') }}
    
                <template #icon v-if="methodData.set">
                  <ph-check-circle size="16" weight="fill" />
                </template>
              </base-badge>
            </div>
  
            <p :class="{ 'block-margin': methodData.set }">
              {{ t(`views.manageMfa.${method}.description.${methodData.set ? 'set' : 'notSet'}`) }}
            </p>

            <template v-if="methodData.set && (methodData.setupDate || methodData.lastUsedDate)">
              <p class="authentication-method-details">
                <template v-if="methodData.setupDate">
                  {{ t('views.manageMfa.setupDate') }}: {{ methodData.setupDate }}
                </template>
                <template v-if="methodData.lastUsedDate">
                  | {{ t('views.manageMfa.lastUsedDate') }}: {{ methodData.lastUsedDate }}
                </template>
              </p>
            </template>

            <template v-if="method === AUTHENTICATION_METHODS.RECOVERY_CODES && methodData.set && typeof methodData.totalCodes === 'number'">
              <p class="authentication-method-details">
                {{ t('views.manageMfa.remainingCodes', { remaining: methodData.remainingCodes ?? 0, total: methodData.totalCodes }) }}
              </p>
            </template>
          </div>

          <div class="authentication-method-actions">
            <template v-if="methodData.set">
              <primary-button :data-testid="`mfa-${method}-edit-button`" variant="outline" size="small" @click="handleEdit(method)">
                {{ t('views.manageMfa.actions.edit') }}
              </primary-button>
              <link-button :data-testid="`mfa-${method}-remove-button`" size="small" @click="handleRemove(method, methodData)">
                {{ t('views.manageMfa.actions.remove') }}
              </link-button>
            </template>
            <template v-else>
              <primary-button :data-testid="`mfa-${method}-setup-button`" variant="outline" size="small" @click="handleSetUp(method)">
                {{ t('views.manageMfa.actions.setUp') }}
              </primary-button>
            </template>
          </div>

          <visual-divider
            v-if="index < authenticationMethodEntries.length - 1"
            class="authentication-method-divider"
          />
        </div>
      </template>
    </div>
  </div>

  <!-- Modals -->
  <manage-authenticator-app-modal
    ref="manageAuthenticatorAppModal"
    @configured="handleAuthenticatorConfigured"
    @reauth-required="handleAuthenticatorReauthRequired"
  />
  <manage-recovery-codes-modal
    ref="manageRecoveryCodesModal"
    @configured="setRecoveryCodesCredentials"
    @reauth-required="handleAuthenticatorReauthRequired"
  />
  <verify-your-identity-modal
    ref="verifyYourIdentityModal"
    :reauth-url="reauthenticationUrl"
  />
  <generic-modal
    ref="removeAuthenticatorModal"
    :title="t('views.manageMfa.confirmRemoveAuthenticatorApp')"
    @close="pendingRemove = null"
  >
    <p class="remove-mfa-method-description">
      {{ t('views.manageMfa.confirmRemoveAuthenticatorAppDescription') }}
    </p>

    <div class="remove-mfa-method-actions">
      <link-button :disabled="isRemoving" @click="cancelRemove">
        {{ t('views.manageMfa.actions.cancel') }}
      </link-button>
      <primary-button :disabled="isRemoving" @click="confirmRemove">
        {{ t('views.manageMfa.actions.remove') }}
      </primary-button>
    </div>
  </generic-modal>
  <generic-modal
    ref="removeRecoveryCodesModal"
    :title="t('views.manageMfa.confirmRemoveRecoveryCodes')"
    @close="pendingRemove = null"
  >
    <p class="remove-mfa-method-description">
      {{ t('views.manageMfa.confirmRemoveRecoveryCodesDescription') }}
    </p>

    <div class="remove-mfa-method-actions">
      <link-button :disabled="isRemoving" @click="cancelRemove">
        {{ t('views.manageMfa.actions.cancel') }}
      </link-button>
      <primary-button :disabled="isRemoving" @click="confirmRemove">
        {{ t('views.manageMfa.actions.remove') }}
      </primary-button>
    </div>
  </generic-modal>
</template>

<style scoped>
.authentication-methods-container {
  border: 1px solid var(--colour-neutral-border);
  border-radius: 0.5rem;
  background-color: white;

  header {
    padding: 1rem 1.125rem;
    border-radius: 0.5rem 0.5rem 0 0;
    color: var(--colour-ti-base);
    background-color: #262d3b; /* TODO: --colour-neutral-raised forced dark */
    font-size: 1.25rem;
    font-weight: 500;
  }

  .authentication-methods-content {
    padding: 1rem 1.5rem 2rem;
    border-radius: 0 0 0.5rem 0.5rem;

    .authentication-method {
      display: grid;
      grid-template-columns: auto 15%;
      column-gap: 2.5rem;
      color: var(--colour-ti-secondary);

      .authentication-method-header {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
        margin-block-end: 0.25rem;

        h3 {
          font-size: 1rem;
        }
      }

      .authentication-method-content {
        p {
          font-size: 0.875rem;
          line-height: 1.23;

          &.block-margin {
            margin-block-end: 1rem;
          }

          &.authentication-method-details {
            font-size: 0.75rem;
            line-height: normal;
            margin-block-end: 0;
          }
        }
      }

      .authentication-method-actions {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;

        button.link {
          color: var(--colour-ti-secondary);
        }
      }

      .authentication-method-divider {
        grid-column: 1 / -1;
        margin-block: 1rem;
      }
    }

    .error-message {
      color: var(--colour-danger-default, #d32f2f);
    }

  }
}

.remove-mfa-method-description {
  color: var(--colour-ti-secondary);
  line-height: 1.32;
  margin-block-end: 1.5rem;
  text-align: center;
}

.remove-mfa-method-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  width: 100%;
}
</style>