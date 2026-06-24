<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';
import GenericModal from '@/components/GenericModal.vue';

defineProps<{
  title: string;
  description: string;
  isRemoving?: boolean;
}>();

const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
  (e: 'close'): void;
}>();

const { t } = useI18n();
const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

defineExpose({
  open: () => genericModal.value.open(),
  close: () => genericModal.value.close(),
});
</script>

<template>
  <generic-modal ref="genericModal" :title="title" @close="emit('close')">
    <p class="remove-mfa-method-description">{{ description }}</p>

    <div class="remove-mfa-method-actions">
      <link-button :disabled="isRemoving" @click="emit('cancel')">
        {{ t('views.manageMfa.actions.cancel') }}
      </link-button>
      <primary-button :disabled="isRemoving" @click="emit('confirm')">
        {{ t('views.manageMfa.actions.remove') }}
      </primary-button>
    </div>
  </generic-modal>
</template>

<style scoped>
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
