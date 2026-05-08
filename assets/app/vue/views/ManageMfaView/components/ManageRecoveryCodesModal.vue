<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { CheckboxInput, LinkButton, PrimaryButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import GenericModal from '@/components/GenericModal.vue';
import { RecoveryCodesCredential, regenerateRecoveryCodes } from '../api';
import { useMfaAction } from '../useMfaAction';

enum MODAL_STEPS {
  CONFIRM = 'confirm',
  CODES = 'codes',
}

const { t } = useI18n();
const { isLoading, errorMessage, run } = useMfaAction();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const step = ref<MODAL_STEPS>(MODAL_STEPS.CONFIRM);
const codes = ref<string[]>([]);
const acknowledged = ref(false);
const justCopied = ref(false);

const emit = defineEmits<{
  (e: 'configured', credentials: RecoveryCodesCredential[]): void;
  (e: 'reauth-required', reauthUrl: string): void;
}>();

// Single-step generate+commit. The CONFIRM step has already warned the user that
// continuing resets any existing codes, so we replace the credential immediately and
// surface the new plaintext codes once. There is no pre-commit "pending" state.
const generate = async () => {
  acknowledged.value = false;

  const response = await run(() => regenerateRecoveryCodes(), {
    fallbackErrorKey: 'views.manageMfa.modals.manageRecoveryCodes.error',
    onReauthRequired: (reauthUrl) => {
      genericModal.value.close();
      emit('reauth-required', reauthUrl);
    },
  });
  if (!response) return;

  codes.value = response.codes;
  step.value = MODAL_STEPS.CODES;
  emit('configured', response.credentials);
};

const copyCodes = async () => {
  if (!codes.value.length) return;
  try {
    await navigator.clipboard.writeText(codes.value.join('\n'));
    justCopied.value = true;
    setTimeout(() => {
      justCopied.value = false;
    }, 2000);
  } catch {
    // navigator.clipboard requires a secure context — fail silently here and
    // let the user fall back to selecting the codes directly. Production runs
    // over HTTPS so this only affects local-dev-over-HTTP testing.
  }
};

const downloadCodes = () => {
  if (!codes.value.length) return;
  const blob = new Blob([codes.value.join('\n')], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = t('views.manageMfa.modals.manageRecoveryCodes.downloadFilename');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

defineExpose({
  open: () => {
    step.value = MODAL_STEPS.CONFIRM;
    codes.value = [];
    errorMessage.value = '';
    acknowledged.value = false;
    justCopied.value = false;
    isLoading.value = false;
    genericModal.value.open();
  },
});
</script>

<template>
  <generic-modal
    ref="genericModal"
    :title="t('views.manageMfa.modals.manageRecoveryCodes.title')"
  >
    <div class="manage-recovery-codes-content" data-testid="recovery-codes-modal">
      <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">{{ errorMessage }}</notice-bar>

      <template v-if="step === MODAL_STEPS.CONFIRM">
        <p class="warning">{{ t('views.manageMfa.modals.manageRecoveryCodes.confirmDescription') }}</p>

        <div class="confirm-actions">
          <link-button :disabled="isLoading" @click="genericModal.close()">
            {{ t('views.manageMfa.actions.cancel') }}
          </link-button>
          <primary-button data-testid="recovery-codes-continue" :disabled="isLoading" @click="generate">
            {{ isLoading
              ? t('views.manageMfa.modals.manageRecoveryCodes.generating')
              : t('views.manageMfa.modals.manageRecoveryCodes.continue') }}
          </primary-button>
        </div>
      </template>

      <template v-else>
        <p>{{ t('views.manageMfa.modals.manageRecoveryCodes.description') }}</p>

        <ul data-testid="recovery-codes-list" class="codes-list">
          <li v-for="(code, index) in codes" :key="index">
            <span class="code-index">{{ index + 1 }}.</span>
            <code>{{ code }}</code>
          </li>
        </ul>

        <div class="codes-actions">
          <link-button data-testid="recovery-codes-copy" @click="copyCodes">
            {{ justCopied
              ? t('views.manageMfa.modals.manageRecoveryCodes.copied')
              : t('views.manageMfa.modals.manageRecoveryCodes.copy') }}
          </link-button>
          <link-button data-testid="recovery-codes-download" @click="downloadCodes">
            {{ t('views.manageMfa.modals.manageRecoveryCodes.download') }}
          </link-button>
        </div>

        <checkbox-input
          data-testid="recovery-codes-ack"
          name="recovery-codes-ack"
          :label="t('views.manageMfa.modals.manageRecoveryCodes.savedConfirmation')"
          v-model="acknowledged"
        />

        <div class="done-action">
          <primary-button
            data-testid="recovery-codes-done"
            :disabled="!acknowledged"
            @click="genericModal.close()"
          >
            {{ t('views.manageMfa.modals.manageRecoveryCodes.done') }}
          </primary-button>
        </div>
      </template>
    </div>
  </generic-modal>
</template>

<style scoped>
.manage-recovery-codes-content {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 1rem;
}

p {
  font-size: 1rem;
  line-height: 1.32;
  color: var(--colour-ti-base);

  &.warning {
    font-size: 0.875rem;
    color: var(--colour-ti-secondary);
  }

  &.loading-state {
    text-align: center;
    color: var(--colour-ti-secondary);
  }
}

.codes-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem 1.5rem;
  padding: 1rem 1.5rem;
  border: 1px solid var(--colour-neutral-border);
  border-radius: 0.5rem;
  background-color: var(--colour-neutral-base);

  li {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
  }

  .code-index {
    color: var(--colour-ti-secondary);
    font-size: 0.75rem;
    min-width: 1.5rem;
    text-align: right;
  }

  code {
    font-size: 0.95rem;
    letter-spacing: 0.08em;
    color: var(--colour-ti-base);
  }
}

.codes-actions {
  display: flex;
  gap: 1.5rem;
  justify-content: center;

  button {
    padding: 0;
  }
}

.done-action {
  display: flex;
  justify-content: flex-end;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  width: 100%;
}
</style>
