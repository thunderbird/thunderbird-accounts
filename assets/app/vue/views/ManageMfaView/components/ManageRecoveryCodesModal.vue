<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { CheckboxInput, LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';
import GenericModal from '@/components/GenericModal.vue';
import {
  confirmRecoveryCodesSetup,
  MfaReauthenticationRequiredError,
  RecoveryCodesCredential,
  startRecoveryCodesSetup,
} from '../api';

const { t } = useI18n();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const codes = ref<string[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const errorMessage = ref('');
const acknowledged = ref(false);
const justCopied = ref(false);

const emit = defineEmits<{
  (e: 'configured', credentials: RecoveryCodesCredential[]): void;
  (e: 'reauth-required', reauthUrl: string): void;
}>();

const generate = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  acknowledged.value = false;

  try {
    const response = await startRecoveryCodesSetup();
    codes.value = response.codes;
  } catch (error) {
    if (error instanceof MfaReauthenticationRequiredError) {
      genericModal.value.close();
      emit('reauth-required', error.reauthUrl);
      return;
    }

    errorMessage.value = error instanceof Error
      ? error.message
      : t('views.manageMfa.modals.manageRecoveryCodes.error');
  } finally {
    isLoading.value = false;
  }
};

const saveCodes = async () => {
  if (!acknowledged.value || isSaving.value) return;

  isSaving.value = true;
  errorMessage.value = '';

  try {
    const response = await confirmRecoveryCodesSetup();
    emit('configured', response.credentials);
    genericModal.value.close();
  } catch (error) {
    if (error instanceof MfaReauthenticationRequiredError) {
      genericModal.value.close();
      emit('reauth-required', error.reauthUrl);
      return;
    }

    errorMessage.value = error instanceof Error
      ? error.message
      : t('views.manageMfa.modals.manageRecoveryCodes.error');
  } finally {
    isSaving.value = false;
  }
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
  open: async () => {
    codes.value = [];
    errorMessage.value = '';
    acknowledged.value = false;
    justCopied.value = false;
    isSaving.value = false;
    genericModal.value.open();
    await generate();
  },
});
</script>

<template>
  <generic-modal
    ref="genericModal"
    :title="t('views.manageMfa.modals.manageRecoveryCodes.title')"
  >
    <div class="manage-recovery-codes-content">
      <p>{{ t('views.manageMfa.modals.manageRecoveryCodes.description') }}</p>
      <p class="warning">{{ t('views.manageMfa.modals.manageRecoveryCodes.regenerateWarning') }}</p>

      <p class="error-message" v-if="errorMessage">{{ errorMessage }}</p>

      <template v-if="isLoading">
        <p class="loading-state">{{ t('views.manageMfa.modals.manageRecoveryCodes.generating') }}</p>
      </template>

      <template v-else-if="codes.length">
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
            :disabled="!acknowledged || isSaving"
            @click="saveCodes"
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

.error-message {
  color: var(--colour-danger-default, #d32f2f);
}
</style>
