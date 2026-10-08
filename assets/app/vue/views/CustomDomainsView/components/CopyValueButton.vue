<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCheck, PhCopySimple } from '@phosphor-icons/vue';

const COPIED_FEEDBACK_MS = 2000;

const { t } = useI18n();

const props = defineProps<{
  value: string;
  label?: string;
}>();

const isCopied = ref(false);
let resetTimeout: ReturnType<typeof setTimeout> | undefined;

const copy = async () => {
  try {
    await navigator.clipboard.writeText(props.value);
  } catch (error) {
    console.error(error);
    return;
  }

  isCopied.value = true;
  clearTimeout(resetTimeout);
  resetTimeout = setTimeout(() => {
    isCopied.value = false;
  }, COPIED_FEEDBACK_MS);
};

onBeforeUnmount(() => clearTimeout(resetTimeout));
</script>

<template>
  <button
    type="button"
    class="copy-value-button"
    :aria-label="label ?? t('views.customDomains.dnsRecords.copy')"
    :title="label ?? t('views.customDomains.dnsRecords.copy')"
    @click="copy"
  >
    <ph-check v-if="isCopied" size="16" aria-hidden="true" />
    <ph-copy-simple v-else size="16" aria-hidden="true" />
  </button>
</template>

<style scoped>
.copy-value-button {
  all: unset;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.5rem;
  color: var(--colour-ti-secondary);
  cursor: pointer;

  &:hover {
    color: var(--colour-ti-base);
    background-color: rgba(0, 0, 0, 0.05);
  }

  &:focus-visible {
    outline: 2px solid var(--colour-primary-default);
    outline-offset: -2px;
  }
}
</style>
