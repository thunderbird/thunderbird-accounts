<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { CheckboxInput, LinkButton, PrimaryButton, TextInput } from '@thunderbirdops/services-ui';
import GenericModal from '@/components/GenericModal.vue';

enum MODAL_STEPS {
  QR = 'qr',
  CODE = 'code',
}

const { t } = useI18n();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const step = ref<MODAL_STEPS>(MODAL_STEPS.QR);
const code = ref('');

const goToCodeStep = () => {
  step.value = MODAL_STEPS.CODE;
};

const submitOneTimeCode = () => {
  if (!code.value) return;
};

defineExpose({
  open: () => {
    step.value = MODAL_STEPS.QR;
    code.value = '';
    genericModal.value.open();
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
          <div class="qr-image" aria-hidden="true" />
          <span class="qr-note">{{ t('views.manageMfa.modals.manageAuthenticatorApp.qrNote') }}</span>
        </div>

        <div class="actions-row">
          <div class="left-actions">
            <link-button>{{ t('views.manageMfa.modals.manageAuthenticatorApp.enterCodeManually') }}</link-button>
            <link-button>{{ t('views.manageMfa.modals.manageAuthenticatorApp.cantScan') }}</link-button>
          </div>

          <primary-button @click="goToCodeStep">{{ t('views.manageMfa.modals.manageAuthenticatorApp.continue') }}</primary-button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="code-step">
        <p>
          {{ t('views.manageMfa.modals.manageAuthenticatorApp.authenticatorAppCodeDescription') }}
        </p>

        <text-input class="code-input" name="one-time-code" v-model="code" :required="true">
          {{ t('views.manageMfa.modals.manageAuthenticatorApp.oneTimeCode') }}
        </text-input>

        <checkbox-input
          :name="t('views.manageMfa.modals.manageAuthenticatorApp.signOutFromOtherDevices')"
          :label="t('views.manageMfa.modals.manageAuthenticatorApp.signOutFromOtherDevices')"
        />
      </div>

      <div class="code-actions">
        <div class="left-actions">
          <link-button>
            {{ t('views.manageMfa.modals.manageAuthenticatorApp.didntGetCode') }}
          </link-button>
        </div>
        <primary-button :disabled="!code || code.trim().length === 0" @click="submitOneTimeCode">
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
  color: #272727; /* TODO: not a variable in the Design System */

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
    width: 224px;
    height: 224px;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
    background-color: var(--colour-neutral-base);
    margin-block-end: 1.5rem;
  }

  .qr-note {
    font-size: 0.75rem;
    color: var(--colour-ti-base);
    text-align: center;
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