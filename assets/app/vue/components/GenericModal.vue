<script setup lang="ts">
import { useId, useTemplateRef } from 'vue';
import { PhX } from '@phosphor-icons/vue';

const props = withDefaults(
  defineProps<{
    title: string;
    /** When false the close button is hidden and Escape is ignored, e.g. while a request is in flight. */
    dismissible?: boolean;
  }>(),
  { dismissible: true },
);

const modal = useTemplateRef<HTMLDialogElement>('modal');
const titleId = useId();

const handleClose = () => {
  modal.value.close();
}

// Escape triggers the dialog's native cancel; swallow it while the caller asked not to be dismissed.
const handleCancel = (event: Event) => {
  if (!props.dismissible) {
    event.preventDefault();
  }
}

const emit = defineEmits<{
  (e: 'close'): void;
}>();

defineExpose({
  open: () => {
    modal.value.showModal();
  },
  close: handleClose,
});
</script>

<template>
  <!-- The native close event fires for the button, close() and Escape alike, so parents hear about all of them. -->
  <dialog ref="modal" :aria-labelledby="titleId" @close="emit('close')" @cancel="handleCancel">
    <button
      v-if="dismissible"
      class="close-button"
      @click="handleClose"
      :aria-label="$t('components.genericModal.close')"
    >
      <ph-x size="24" aria-hidden="true" />
    </button>

    <div class="modal-scroll-area">
      <div class="modal-content">
        <h2 :id="titleId">{{ title }}</h2>

        <slot />
      </div>
    </div>
    <div v-if="$slots.actions" class="modal-actions">
      <slot name="actions" />
    </div>
  </dialog>
</template>

<style scoped>
dialog {
  --modal-inset-block-start: 1rem;
  position: fixed;
  top: var(--modal-inset-block-start);
  left: 50%;
  transform: translate(-50%, 0);
  margin: 0;
  background-color: var(--colour-neutral-base);
  border-radius: 1.5rem;
  border: none;
  box-shadow: 0.25rem 0.25rem 1rem 0 rgba(0, 0, 0, 0.04);
  padding: 2rem 1rem 1.5rem;
  width: 640px;
  max-width: 90vw;
  max-height: calc(100vh - var(--modal-inset-block-start) * 2);
  max-height: calc(100dvh - var(--modal-inset-block-start) * 2);
  overflow: hidden;

  &[open] {
    display: flex;
    flex-direction: column;
  }

  &::backdrop {
    background-color: var(--colour-neutral-900);
    opacity: 0.5;
  }

  .modal-scroll-area {
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .close-button {
    position: absolute;
    top: 1rem;
    right: 1rem;
    z-index: 1;
    background-color: rgba(0, 0, 0, 0.05);
    color: rgba(0, 0, 0, 0.5);
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05);
    border: none;
    border-radius: 999px;
    padding: 0.5rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      background-color: rgba(0, 0, 0, 0.1);
    }
  }

  .modal-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-inline: 1rem;
    padding-block-end: 0.5rem;

    h2 {
      font-family: metropolis;
      font-size: 1.5rem;
      font-weight: 500;
      line-height: 1.2;
      color: var(--colour-ti-highlight);
      padding-inline: 2rem;
      margin-block: 1.5rem 1.75rem;
      text-align: center;
    }
  }

  .modal-actions {
    display: flex;
    flex-wrap: wrap;
    flex-shrink: 0;
    justify-content: flex-end;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem 1rem 0;
  }
}

@media (min-width: 768px) and (min-height: 600px) {
  dialog {
    --modal-inset-block-start: 144px;
  }
}
</style>
