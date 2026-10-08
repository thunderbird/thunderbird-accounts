<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import CardContainer from '@/components/CardContainer.vue';
import StepIndicator from '@/components/StepIndicator.vue';
import Step1Add from './components/Step1Add.vue';
import Step2Identify from './components/Step2Identify.vue';

const { t } = useI18n();
const router = useRouter();

const currentStep = ref(0);
const customDomain = ref<string | null>(null);
const dnsProvider = ref<string | null>(null);

const steps = computed(() => [
  { key: 'add', label: t('views.customDomains.steps.add') },
  { key: 'update-records', label: t('views.customDomains.steps.updateRecords') },
  { key: 'summary', label: t('views.customDomains.steps.summary') },
]);

const onCancel = () => {
  router.push('/settings');
};

const onDomainAdded = (domainName: string) => {
  customDomain.value = domainName;
  currentStep.value = 1;
};

const onProviderSelected = (provider: string) => {
  dnsProvider.value = provider;
  // TODO: advance to Step3 once it exists
};
</script>

<script lang="ts">
export default {
  name: 'CustomDomainsView',
};
</script>

<template>
  <card-container>
    <step-indicator
      class="steps"
      :steps="steps"
      :current-step="currentStep"
      :aria-label="t('views.customDomains.stepsLabel')"
    />

    <step1-add v-if="currentStep === 0" @cancel="onCancel" @added="onDomainAdded" />
    <step2-identify
      v-else-if="currentStep === 1 && customDomain"
      :domain-name="customDomain"
      @cancel="onCancel"
      @continue="onProviderSelected"
    />
  </card-container>
</template>

<style scoped>
.steps {
  margin-block-end: 2rem;
}
</style>
