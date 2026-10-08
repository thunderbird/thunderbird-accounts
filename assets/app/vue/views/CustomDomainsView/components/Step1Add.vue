<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput } from '@thunderbirdops/services-ui';
import { addCustomDomain } from '../api';

const { t } = useI18n();

const emit = defineEmits<{
  cancel: [];
  added: [domainName: string];
}>();

const domainName = ref<string>('');
const error = ref<string | null>(null);
const isAdding = ref(false);

const onSubmit = async () => {
  const submittedDomain = domainName.value.trim();
  if (!submittedDomain || isAdding.value) {
    return;
  }

  isAdding.value = true;
  error.value = null;

  try {
    const data = await addCustomDomain(submittedDomain);

    if (data.success) {
      emit('added', data.domain_name ?? submittedDomain);
    } else {
      console.error(data.error);
      error.value = data.error ?? '';
    }
  } catch (e) {
    console.error(e);
    error.value = String(e);
  } finally {
    isAdding.value = false;
  }
};
</script>

<template>
  <section class="step-add">
    <h2>{{ t('views.customDomains.stepAdd.title') }}</h2>
    <p class="description">{{ t('views.customDomains.stepAdd.description') }}</p>

    <form @submit.prevent="onSubmit">
      <text-input
        v-model="domainName"
        name="custom-domain"
        class="domain-input"
        :placeholder="t('views.customDomains.stepAdd.domainPlaceholder')"
        :error="error"
        required
      >
        {{ t('views.customDomains.stepAdd.domainName') }}
      </text-input>

      <div class="actions">
        <primary-button type="button" variant="outline" @click="emit('cancel')">
          {{ t('views.customDomains.stepAdd.cancel') }}
        </primary-button>
        <primary-button type="primary" :disabled="isAdding || !domainName.trim()">
          {{ t('views.customDomains.stepAdd.addDomain') }}
        </primary-button>
      </div>
    </form>

    <router-link to="/contact" class="help-link">
      {{ t('views.customDomains.stepAdd.needHelp') }}
    </router-link>
  </section>
</template>

<style scoped>
.step-add {
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

  .domain-input {
    margin-block-end: 1.5rem;
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
  .step-add .domain-input {
    max-width: 50%;
  }
}
</style>
