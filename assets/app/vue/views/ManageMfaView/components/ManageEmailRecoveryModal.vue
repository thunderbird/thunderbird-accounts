<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { LinkButton, PrimaryButton, TextInput } from '@thunderbirdops/services-ui';
import GenericModal from '@/components/GenericModal.vue';

const { t } = useI18n();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const email = ref('');
const submittedEmail = ref('');

const sendCode = () => {
  if (!email.value || email.value.trim().length === 0) return;
  submittedEmail.value = email.value;
};

const continueAction = () => {
  // Placeholder for continue action
};

defineExpose({
  open: () => {
    email.value = '';
    submittedEmail.value = '';
    genericModal.value.open();
  },
});
</script>

<template>
  <generic-modal
    ref="genericModal"
    :title="t('views.manageMfa.modals.manageEmailRecovery.title')"
  >
    <div class="manage-email-recovery-content">
      <p>
        {{ t('views.manageMfa.modals.manageEmailRecovery.description') }}
      </p>

      <div class="email-row">
        <text-input class="email-input" name="recovery-email" v-model="email" required>
          {{ t('views.manageMfa.modals.manageEmailRecovery.email') }}
        </text-input>
        <primary-button variant="outline" @click="sendCode">
          {{ t('views.manageMfa.modals.manageEmailRecovery.sendCode') }}
        </primary-button>
      </div>

      <p v-if="submittedEmail" class="sent-note">
        {{ t('views.manageMfa.modals.manageEmailRecovery.sentTo', { email: submittedEmail }) }}
      </p>

      <div class="code-actions">
        <div class="left-actions">
          <link-button>
            {{ t('views.manageMfa.modals.manageEmailRecovery.didntGetCode') }}
          </link-button>
        </div>
        <primary-button :disabled="!submittedEmail" @click="continueAction">
          {{ t('views.manageMfa.modals.manageEmailRecovery.continue') }}
        </primary-button>
      </div>
    </div>
  </generic-modal>
</template>

<style scoped>
p {
  font-size: 1rem;
  line-height: 1.23;
  color: #272727; /* TODO: not a variable in the Design System */
}

.manage-email-recovery-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.email-row {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  width: 100%;

  .email-input {
    flex: 1;
  }

  button {
    margin-block-start: 1.625rem;
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

.sent-note {
  font-size: 0.75rem;
  color: var(--colour-ti-base);
  text-align: center;
}
</style>