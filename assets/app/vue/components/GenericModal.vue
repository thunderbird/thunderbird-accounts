<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { PhX } from '@phosphor-icons/vue';

defineProps<{
  title: string;
}>();

const modal = useTemplateRef<HTMLDialogElement>('modal');

const handleClose = () => {
  modal.value.close();
  emit('close');
}

const handleBackdropClick = (event: MouseEvent) => {
  if (event.target === modal.value) {
    handleClose();
  }
}

const emit = defineEmits<{
  (e: 'close'): void;
}>();

defineExpose({
  open: () => {
    modal.value.showModal();
  },
});
</script>

<template>
  <dialog ref="modal" @click="handleBackdropClick">
    <button class="close-button" @click="handleClose">
      <ph-x size="24" />
    </button>

    <div class="modal-content">
      <h2>{{ title }}</h2>

      <slot />
    </div>
  </dialog>
</template>

<style scoped>
dialog {
  position: fixed;
  top: 144px;
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
  max-height: 90vh;
  overflow: auto;

  &::backdrop {
    background-color: var(--colour-neutral-900);
    opacity: 0.5;
  }

  .close-button {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background-color: rgba(0, 0, 0, 0.05);
    color: rgba(0, 0, 0, 0.5);
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05);
    border: none;
    border-radius: 999px;
    padding: 0.5rem;
    cursor: pointer;

    &:hover {
      background-color: rgba(0, 0, 0, 0.1);
    }
  }

  .modal-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    padding-inline: 1rem;

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
}
</style>
