<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, SelectInput } from '@thunderbirdops/services-ui';
import { getDnsProviders } from '../api';

const { t } = useI18n();

defineProps<{
  domainName: string;
}>();

const emit = defineEmits<{
  cancel: [];
  continue: [provider: string];
}>();

const ICANN_LOOKUP_URL = 'https://lookup.icann.org/';

const providers = computed(() => [
  { label: t('views.customDomains.stepIdentify.dnsProviderPlaceholder'), value: '' },
  ...getDnsProviders(),
]);
const selectedProvider = ref<string>('');

const onSubmit = () => {
  if (!selectedProvider.value) {
    return;
  }

  emit('continue', selectedProvider.value);
};
</script>

<template>
  <section class="step-identify">
    <h2>{{ t('views.customDomains.stepIdentify.title', { domain: domainName }) }}</h2>
    <p class="description">{{ t('views.customDomains.stepIdentify.description') }}</p>

    <form @submit.prevent="onSubmit">
      <div class="provider-select">
        <select-input v-model="selectedProvider" name="dns-provider" :options="providers" required>
          {{ t('views.customDomains.stepIdentify.dnsProvider') }}
        </select-input>
      </div>

      <i18n-t keypath="views.customDomains.stepIdentify.notSure" tag="p" class="help-text">
        <template #link>
          <a :href="ICANN_LOOKUP_URL" target="_blank" rel="noopener noreferrer">
            {{ t('views.customDomains.stepIdentify.icannLookup') }}
          </a>
        </template>
      </i18n-t>

      <div class="actions">
        <primary-button form-action="none" variant="outline" @click="emit('cancel')">
          {{ t('views.customDomains.stepIdentify.cancel') }}
        </primary-button>
        <primary-button form-action="submit" :disabled="!selectedProvider">
          {{ t('views.customDomains.stepIdentify.continue') }}
        </primary-button>
      </div>
    </form>

    <router-link to="/contact" class="help-link">
      {{ t('views.customDomains.stepIdentify.needHelp') }}
    </router-link>
  </section>
</template>

<style scoped>
.step-identify {
  h2 {
    font-family: metropolis;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--colour-ti-highlight);
    margin-block-end: 0.5rem;
  }

  .description {
    font-size: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
    margin-block-end: 1.5rem;
  }

  .provider-select {
    margin-block-end: 0.5rem;
  }

  .help-text {
    font-size: 0.8125rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
    margin-block-end: 1.5rem;

    a {
      color: inherit;
    }
  }

  .actions {
    display: flex;
    gap: 1rem;
    margin-block-end: 2rem;
  }

  .help-link {
    color: var(--colour-ti-secondary);
    font-size: 1rem;
  }
}

@media (min-width: 768px) {
  .step-identify .provider-select {
    max-width: 50%;
  }
}
</style>
