<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCaretDown, PhCaretRight } from '@phosphor-icons/vue';
import { DNS_FORMATTING_SUPPORT_URL } from '@/defines';

const { t } = useI18n();

const props = withDefaults(defineProps<{
  title?: string;
  defaultOpen?: boolean;
}>(), {
  title: undefined,
  defaultOpen: true,
});

const isOpen = ref(props.defaultOpen);
</script>

<template>
  <section class="dns-format-panel">
    <button
      type="button"
      class="panel-toggle"
      :aria-expanded="isOpen"
      aria-controls="dns-format-content"
      @click="isOpen = !isOpen"
    >
      <ph-caret-down v-if="isOpen" size="20" aria-hidden="true" />
      <ph-caret-right v-else size="20" aria-hidden="true" />
      <span>{{ title ?? t('views.customDomains.verificationResults.formatPanel.title') }}</span>
    </button>

    <div v-show="isOpen" id="dns-format-content" class="panel-content">
      <i18n-t keypath="views.customDomains.verificationResults.formatPanel.description" tag="p">
        <template #name><strong>{{ t('views.customDomains.verificationResults.formatPanel.name') }}</strong></template>
        <template #host><strong>{{ t('views.customDomains.verificationResults.formatPanel.host') }}</strong></template>
      </i18n-t>
      <p>{{ t('views.customDomains.verificationResults.formatPanel.checkDocumentation') }}</p>
      <a :href="DNS_FORMATTING_SUPPORT_URL" target="_blank" rel="noopener noreferrer">
        {{ t('views.customDomains.verificationResults.formatPanel.learnMore') }}
      </a>
    </div>
  </section>
</template>

<style scoped>
.dns-format-panel {
  border: 1px solid var(--colour-neutral-border);
  border-radius: 0.5rem;
  margin-block-end: 1.5rem;

  .panel-toggle {
    all: unset;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem 1rem;
    font-family: metropolis, sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: var(--colour-ti-secondary);
    cursor: pointer;

    &:focus-visible {
      outline: 2px solid var(--colour-primary-default);
      outline-offset: 2px;
    }
  }

  .panel-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-inline: 1rem;
    padding-block: 1rem 1.25rem;
    border-block-start: 1px solid var(--colour-neutral-border);
    font-size: 0.875rem;
    line-height: 1.4;
    color: var(--colour-ti-secondary);

    p {
      margin: 0;
    }

    a {
      color: var(--colour-primary-default);
      width: fit-content;
    }
  }
}
</style>
