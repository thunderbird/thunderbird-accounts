<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { PhKey } from '@phosphor-icons/vue';
import GenericModal from '@/components/GenericModal.vue';

enum METHODS {
  AUTHENTICATOR_APP = 'authenticator-app',
}

const { t } = useI18n();

const method = ref<METHODS>(METHODS.AUTHENTICATOR_APP);
const errorMessage = ref('');
const isLoading = ref(false);
const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const props = defineProps<{
  reauthUrl?: string;
}>();

const goToCodeStep = async () => {
  if (!method.value) return;

  if (method.value === METHODS.AUTHENTICATOR_APP) {
    const fallback = `/oidc/mfa-reauth/?next=${encodeURIComponent(window.location.pathname)}`;
    window.location.assign(props.reauthUrl || fallback);
    return;
  }
};

defineExpose({
  open: () => {
    method.value = METHODS.AUTHENTICATOR_APP;
    errorMessage.value = '';
    isLoading.value = false;
    genericModal.value.open();
  },
});
</script>

<template>
  <generic-modal
    ref="genericModal"
    :title="t('views.manageMfa.modals.verifyYourIdentity.title')"
  >
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
    </div>

    <p class="error-message" v-if="errorMessage">{{ errorMessage }}</p>

    <div class="verify-your-identity-options-actions">
      <primary-button :disabled="isLoading || !method" @click="goToCodeStep">
        {{ t('views.manageMfa.modals.verifyYourIdentity.verify') }}
      </primary-button>
    </div>
  </generic-modal>
</template>

<style scoped>
p {
  font-size: 1rem;
  line-height: 1.32;
  color: var(--colour-ti-base);
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

.verify-your-identity-options-actions {
  display: flex;
  width: 100%;
  justify-content: flex-end;
}

.error-message {
  color: var(--colour-danger-default, #d32f2f);
}
</style>
