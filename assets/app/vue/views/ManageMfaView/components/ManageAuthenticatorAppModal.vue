<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { CheckboxInput, LinkButton, PrimaryButton, TextInput } from '@thunderbirdops/services-ui';
import encodeQR from 'qr';
import GenericModal from '@/components/GenericModal.vue';
import {
  confirmTotpSetup,
  MfaReauthenticationRequiredError,
  startTotpSetup,
  TotpCredential,
  TotpSetupResponse,
} from '../api';

enum MODAL_STEPS {
  QR = 'qr',
  CODE = 'code',
}

const { t } = useI18n();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const step = ref<MODAL_STEPS>(MODAL_STEPS.QR);
const code = ref('');
const setup = ref<TotpSetupResponse | null>(null);
const isLoading = ref(false);
const errorMessage = ref('');
const showManualSecret = ref(false);
const logoutOtherSessions = ref(false);

const qrCode = computed(() => setup.value?.otpAuthUri ? encodeURIComponent(encodeQR(setup.value.otpAuthUri, 'svg')) : '');

const emit = defineEmits<{
  (e: 'configured', credentials: TotpCredential[]): void;
  (e: 'reauth-required', reauthUrl: string): void;
}>();

const goToCodeStep = () => {
  step.value = MODAL_STEPS.CODE;
};

const submitOneTimeCode = async () => {
  if (!code.value) return;
  isLoading.value = true;
  errorMessage.value = '';

  try {
    const response = await confirmTotpSetup(code.value, logoutOtherSessions.value);
    // Close before emitting so the parent can chain another modal (e.g. recovery codes)
    // without two dialogs overlapping in the top layer.
    genericModal.value.close();
    emit('configured', response.credentials);
  } catch (error) {
    if (error instanceof MfaReauthenticationRequiredError) {
      genericModal.value.close();
      emit('reauth-required', error.reauthUrl);
      return;
    }

    errorMessage.value = error instanceof Error ? error.message : t('views.manageMfa.modals.manageAuthenticatorApp.error');
  } finally {
    isLoading.value = false;
  }
};

defineExpose({
  open: async () => {
    step.value = MODAL_STEPS.QR;
    code.value = '';
    setup.value = null;
    errorMessage.value = '';
    showManualSecret.value = false;
    logoutOtherSessions.value = false;
    genericModal.value.open();

    try {
      setup.value = await startTotpSetup();
    } catch (error) {
      if (error instanceof MfaReauthenticationRequiredError) {
        genericModal.value.close();
        emit('reauth-required', error.reauthUrl);
        return;
      }

      errorMessage.value = error instanceof Error ? error.message : t('views.manageMfa.modals.manageAuthenticatorApp.error');
    }
  },
});
</script>

<template>
  <generic-modal
    ref="genericModal"
    :title="t('views.manageMfa.modals.manageAuthenticatorApp.title')"
  >
    <template v-if="step === MODAL_STEPS.QR">
      <div class="manage-authenticator-app-content">
        <p>{{ t('views.manageMfa.modals.manageAuthenticatorApp.description') }}</p>
        <p class="smaller">{{ t('views.manageMfa.modals.manageAuthenticatorApp.descriptionTwo') }}</p>

        <div class="qr-section">
          <template v-if="setup">
            <img
              data-testid="totp-qr-code"
              class="qr-image"
              :src="`data:image/svg+xml;utf8,${qrCode}`"
              :alt="t('views.manageMfa.modals.manageAuthenticatorApp.qrAlt')"
            />
          </template>
          <div v-else class="qr-image loading" aria-hidden="true" />
          <span class="qr-note">{{ t('views.manageMfa.modals.manageAuthenticatorApp.qrNote') }}</span>
        </div>

        <p class="error-message" v-if="errorMessage">{{ errorMessage }}</p>

        <div class="manual-secret" v-if="showManualSecret && setup">
          <strong>{{ t('views.manageMfa.modals.manageAuthenticatorApp.manualSecret') }}</strong>
          <code data-testid="totp-manual-secret">{{ setup.secret }}</code>
        </div>

        <div class="actions-row">
          <div class="left-actions">
            <link-button data-testid="totp-show-manual-secret" @click="showManualSecret = true">
              {{ t('views.manageMfa.modals.manageAuthenticatorApp.enterCodeManually') }}
            </link-button>
            <link-button>{{ t('views.manageMfa.modals.manageAuthenticatorApp.cantScan') }}</link-button>
          </div>

          <primary-button data-testid="totp-continue-to-code" :disabled="!setup" @click="goToCodeStep">
            {{ t('views.manageMfa.modals.manageAuthenticatorApp.continue') }}
          </primary-button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="code-step">
        <p>
          {{ t('views.manageMfa.modals.manageAuthenticatorApp.authenticatorAppCodeDescription') }}
        </p>

        <text-input data-testid="totp-code-input" class="code-input" name="one-time-code" v-model="code" :required="true">
          {{ t('views.manageMfa.modals.manageAuthenticatorApp.oneTimeCode') }}
        </text-input>

        <p class="error-message" v-if="errorMessage">{{ errorMessage }}</p>

        <checkbox-input
          :name="t('views.manageMfa.modals.manageAuthenticatorApp.signOutFromOtherDevices')"
          :label="t('views.manageMfa.modals.manageAuthenticatorApp.signOutFromOtherDevices')"
          v-model="logoutOtherSessions"
        />
      </div>

      <div class="code-actions">
        <div class="left-actions">
          <link-button>
            {{ t('views.manageMfa.modals.manageAuthenticatorApp.didntGetCode') }}
          </link-button>
        </div>
        <primary-button data-testid="totp-submit-code" :disabled="isLoading || !code || code.trim().length === 0" @click="submitOneTimeCode">
          {{ t('views.manageMfa.modals.manageAuthenticatorApp.continue') }}
        </primary-button>
      </div>
    </template>
  </generic-modal>
</template>

<style scoped>
p {
  font-size: 1rem;
  line-height: 1.23;
  color: var(--colour-ti-base);

  &.smaller {
    font-size: 0.875rem;
  }
}

.manage-authenticator-app-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin-block-start: 0.5rem;

  .qr-image {
    width: 210px;
    height: 180px;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
    background-color: var(--colour-neutral-base);
    margin-block-end: 1.5rem;
    object-fit: contain;

    &.loading {
      background: linear-gradient(90deg, var(--colour-neutral-base), #f5f5f5, var(--colour-neutral-base));
    }
  }

  .qr-note {
    font-size: 0.75rem;
    color: var(--colour-ti-base);
    text-align: center;
  }
}

.manual-secret {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;

  code {
    color: var(--colour-ti-secondary);
    background-color: var(--colour-neutral-base);
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.25rem;
    padding: 0.5rem;
    letter-spacing: 0.08em;
  }
}

.error-message {
  color: var(--colour-danger-default, #d32f2f);
}

.actions-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-block-start: 0.5rem;
}

.left-actions {
  display: flex;
  align-items: center;
  gap: 1rem;

  button {
    padding: 0;
  }
}

.code-step {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-block-end: 1rem;

  p {
    margin-block-end: 1.5rem;
  }

  .code-input {
    margin-block-end: 1.5rem;
  }
}

.code-actions {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;

  .left-actions {
    display: flex;
    align-items: center;

    button {
      padding: 0;
    }
  }
}
</style>
