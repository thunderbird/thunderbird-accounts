<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';

const { t } = useI18n();

defineProps<{
  domainName: string;
}>();

const emit = defineEmits<{
  done: [];
}>();

const primaryEmail = window._page?.userEmail;
</script>

<template>
  <section class="step-summary">
    <h2>{{ t('views.customDomains.stepSummary.title') }}</h2>

    <i18n-t keypath="views.customDomains.stepSummary.description" tag="p" class="description">
      <template #domain>
        <strong>{{ domainName }}</strong>
      </template>
      <template #pending>
        <strong>{{ t('views.customDomains.stepSummary.pending') }}</strong>
      </template>
    </i18n-t>

    <i18n-t keypath="views.customDomains.stepSummary.notifyByEmail" tag="p" class="description">
      <template #email>
        <strong>{{ primaryEmail }}</strong>
      </template>
    </i18n-t>

    <primary-button form-action="none" @click="emit('done')">
      {{ t('views.customDomains.stepSummary.done') }}
    </primary-button>
  </section>
</template>

<style scoped>
.step-summary {
  h2 {
    font-family: metropolis, sans-serif;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--colour-ti-highlight);
    margin-block-end: 1.5rem;
  }

  .description {
    font-size: 1rem;
    line-height: 1.5;
    color: var(--colour-ti-secondary);
    margin-block-end: 1.5rem;
  }
}
</style>
