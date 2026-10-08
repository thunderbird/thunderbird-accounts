<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { CheckboxInput, PrimaryButton } from '@thunderbirdops/services-ui';

const { t } = useI18n();

defineProps<{
  domainName: string;
}>();

const emit = defineEmits<{
  done: [notifyByEmail: boolean];
}>();

const primaryEmail = window._page?.userEmail;
const notifyByEmail = ref(false);
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

    <div class="notify">
      <checkbox-input v-model="notifyByEmail" name="notify-by-email" />
      <i18n-t keypath="views.customDomains.stepSummary.notifyByEmail" tag="label" for="notify-by-email">
        <template #email>
          <strong>{{ primaryEmail }}</strong>
        </template>
      </i18n-t>
    </div>

    <primary-button form-action="none" @click="emit('done', notifyByEmail)">
      {{ t('views.customDomains.stepSummary.done') }}
    </primary-button>
  </section>
</template>

<style scoped>
.step-summary {
  h2 {
    font-family: metropolis;
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

  .notify {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: start;
    gap: 0.5rem;
    margin-block-end: 1.5rem;
    color: var(--colour-ti-secondary);
    line-height: 1.32;

    :deep(.checkbox-wrapper) {
      width: auto;
    }

    label {
      cursor: pointer;
    }
  }
}

@media (min-width: 768px) {
  .step-summary .description {
    max-width: 50%;
  }
}
</style>
