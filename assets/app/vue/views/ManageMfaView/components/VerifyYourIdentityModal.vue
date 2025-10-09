<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput } from '@thunderbirdops/services-ui';
import { PhKey, PhEnvelope } from '@phosphor-icons/vue';
import GenericModal from '@/components/GenericModal.vue';

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const { t } = useI18n();

const step = ref<'select' | 'code'>('select');
const method = ref<'authenticator-app' | 'recovery-email-address'>();
const code = ref('');

const goToCodeStep = () => {
  if (!method.value) return;
  step.value = 'code';
};

const submitOneTimeCode = () => {
  if (!code.value) return;
  console.log('submitOneTimeCode', code.value);
};

defineExpose({
  open: () => {
    step.value = 'select';
    method.value = undefined;
    code.value = '';
    genericModal.value.open();
  },
});
</script>

<template>
  <generic-modal
    ref="genericModal"
    :title="t('views.manageMfa.modals.verifyYourIdentity.title')"
  >
    <template v-if="step === 'select'">
      <p>{{ t('views.manageMfa.modals.verifyYourIdentity.description') }}</p>

      <div class="verify-your-identity-options">
        <input
          class="screen-reader-only"
          type="radio"
          name="verify-your-identity"
          id="authenticator-app"
          v-model="method"
          value="authenticator-app"
        />
        <label class="verify-option" for="authenticator-app">
          <span class="icon"><ph-key size="24" /></span>
          <span class="content">
            <span class="title">
              {{ t('views.manageMfa.modals.verifyYourIdentity.authenticatorApp') }}
            </span>
            <span class="description">
              {{ t('views.manageMfa.modals.verifyYourIdentity.authenticatorAppDescription') }}
            </span>
          </span>
        </label>

        <input
          class="screen-reader-only"
          type="radio"
          name="verify-your-identity"
          id="recovery-email-address"
          v-model="method"
          value="recovery-email-address"
        />
        <label class="verify-option" for="recovery-email-address">
          <span class="icon"><ph-envelope size="24" /></span>
          <span class="content">
            <span class="title">
              {{ t('views.manageMfa.modals.verifyYourIdentity.recoveryEmailAddress') }}
            </span>
            <span class="description">
              {{
                t(
                  'views.manageMfa.modals.verifyYourIdentity.recoveryEmailAddressDescription',
                  { emailAddress: 'test@example.com' }
                )
              }}
            </span>
          </span>
        </label>
      </div>

      <div class="verify-your-identity-options-actions">
        <primary-button :disabled="!method" @click="goToCodeStep">
          {{ t('views.manageMfa.modals.verifyYourIdentity.verify') }}
        </primary-button>
      </div>
    </template>

    <template v-else>
      <div class="verify-your-identity-code-step">
        <p>
          {{
            method === 'authenticator-app'
              ? t('views.manageMfa.modals.verifyYourIdentity.authenticatorAppCodeDescription')
              : t('views.manageMfa.modals.verifyYourIdentity.recoveryEmailAddressCodeDescription')
          }}
        </p>
  
        <text-input name="one-time-code" v-model="code" :required="true">
          {{ t('views.manageMfa.modals.verifyYourIdentity.oneTimeCode') }}
        </text-input>
      </div>

      <div class="verify-your-identity-options-actions">
        <primary-button :disabled="!code || code.trim().length === 0" @click="submitOneTimeCode">
          {{ t('views.manageMfa.modals.verifyYourIdentity.verify') }}
        </primary-button>
      </div>
    </template>
  </generic-modal>
</template>

<style scoped>
p {
  font-size: 1rem;
  line-height: 1.32;
  color: #272727; /* TODO: not a variable in the Design System */
  margin-block-end: 1rem;
}

.verify-your-identity-options {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 1rem;
  margin-block-end: 1rem;
  
  /* Focus ring when the hidden input is focused */
  .screen-reader-only:focus-visible + .verify-option {
    outline: 2px solid var(--colour-service-primary);
    outline-offset: 2px;
  }

  /* Checked styles */
  .screen-reader-only:checked + .verify-option {
    border-color: var(--colour-service-primary);
    background-color: var(--colour-service-soft);
  }

  .verify-option {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
    background-color: var(--colour-neutral-base);
    padding: 0.875rem 1rem;
    cursor: pointer;
    transition: var(--transition);

    &:hover {
      border-color: var(--colour-neutral-border-intense);
    }

    .icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--colour-service-primary);
    }

    .content {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;

      .title {
        font-size: 0.9375rem;
        line-height: 1.2;
        font-weight: 600;
        color: var(--colour-ti-base);
      }

      .description {
        font-size: 0.875rem;
        line-height: 1.23;
        color: var(--colour-ti-secondary);
      }
    }
  }
}

.verify-your-identity-code-step {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-block-end: 1rem;
}

.verify-your-identity-options-actions {
  display: flex;
  width: 100%;
  justify-content: flex-end;
}
</style>
