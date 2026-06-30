<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { LinkButton, PrimaryButton, TextInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import encodeQR from 'qr';
import GenericModal from '@/components/GenericModal.vue';
import { confirmTotpSetup, startTotpSetup, TotpCredential, TotpSetupResponse } from '../api';
import { useMfaAction } from '../useMfaAction';

enum MODAL_STEPS {
  QR = 'qr',
  CODE = 'code',
}

const { t } = useI18n();
const { isLoading, errorMessage, run } = useMfaAction();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const step = ref<MODAL_STEPS>(MODAL_STEPS.QR);
const code = ref('');
const setup = ref<TotpSetupResponse | null>(null);
const showManualSecret = ref(false);

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

  const response = await run(() => confirmTotpSetup(code.value, false), {
    fallbackErrorKey: 'views.manageMfa.modals.manageAuthenticatorApp.error',
    onReauthRequired: (reauthUrl) => {
      genericModal.value.close();
      emit('reauth-required', reauthUrl);
    },
  });
  if (!response) return;

  // Close before emitting so the parent can chain another modal (e.g. recovery codes)
  // without two dialogs overlapping in the top layer.
  genericModal.value.close();
  emit('configured', response.credentials);
};

defineExpose({
  open: async () => {
    step.value = MODAL_STEPS.QR;
    code.value = '';
    setup.value = null;
    errorMessage.value = '';
    showManualSecret.value = false;
    genericModal.value.open();

    const response = await run(() => startTotpSetup(), {
      fallbackErrorKey: 'views.manageMfa.modals.manageAuthenticatorApp.error',
      onReauthRequired: (reauthUrl) => {
        genericModal.value.close();
        emit('reauth-required', reauthUrl);
      },
    });
    if (response) setup.value = response;
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

        <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">{{ errorMessage }}</notice-bar>

        <div class="manual-secret" v-if="showManualSecret && setup">
          <strong>{{ t('views.manageMfa.modals.manageAuthenticatorApp.manualSecret') }}</strong>
          <code data-testid="totp-manual-secret">{{ setup.secret }}</code>
        </div>

        <div class="actions-row">
          <div class="left-actions">
            <link-button data-testid="totp-show-manual-secret" @click="showManualSecret = true">
              {{ t('views.manageMfa.modals.manageAuthenticatorApp.enterCodeManually') }}
            </link-button>
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

        <text-input data-testid="totp-code-input" class="code-input" name="one-time-code" v-model="code" :required="true" :error="errorMessage">
          {{ t('views.manageMfa.modals.manageAuthenticatorApp.oneTimeCode') }}
        </text-input>
      </div>

      <div class="code-actions">
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
  justify-content: flex-end;
}
</style>
