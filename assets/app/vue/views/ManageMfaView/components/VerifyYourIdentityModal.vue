<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhKey } from '@phosphor-icons/vue';
import GenericModal from '@/components/GenericModal.vue';

const { t } = useI18n();

const errorMessage = ref('');
const isLoading = ref(false);
const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const props = defineProps<{
  reauthUrl?: string;
}>();

// We hand off to Keycloak, which presents whichever second factor(s) the user has
// enrolled (authenticator app, recovery code, and more as they're added). The app can't
// preselect one, so this is a confirmation rather than a method picker.
const verify = () => {
  const fallback = `/oidc/mfa-reauth/?next=${encodeURIComponent(window.location.pathname)}`;
  window.location.assign(props.reauthUrl || fallback);
};

defineExpose({
  open: () => {
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
      <div class="verify-option">
        <span class="icon"><ph-key size="24" /></span>
        <span class="content">
          <span class="title">
            {{ t('views.manageMfa.modals.verifyYourIdentity.secondFactor') }}
          </span>
          <span class="description">
            {{ t('views.manageMfa.modals.verifyYourIdentity.secondFactorDescription') }}
          </span>
        </span>
      </div>
    </div>

    <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">{{ errorMessage }}</notice-bar>

    <div class="verify-your-identity-options-actions">
      <primary-button :disabled="isLoading" @click="verify">
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

  .verify-option {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
    background-color: var(--colour-neutral-base);
    padding: 0.875rem 1rem;

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
</style>
