<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import CardContainer from '@/components/CardContainer.vue';
import StepIndicator from '@/components/StepIndicator.vue';
import Step1Add from './components/Step1Add.vue';
import Step2Identify from './components/Step2Identify.vue';
import Step3Summary from './components/Step3Summary.vue';
import VerificationResultsView from './VerificationResultsView/index.vue';
import { useEmailSettings } from '../SettingsView/sections/EmailSettingsSection/useEmailSettings';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const { requestCustomDomainsExpanded } = useEmailSettings();

// An existing domain can be passed in to skip straight to choosing its DNS provider
const initialDomain = typeof route.query.domain === 'string' ? route.query.domain : null;

// The domain actions menu says where to land through the navigation state, which keeps the domain
// out of the URL: on the summary once it has queued a verification, or on the results of a failed one
const entry = (window.history.state ?? {}) as { verificationQueuedDomain?: string; verificationResultsDomain?: string };
const queuedDomain = entry.verificationQueuedDomain ?? null;
const resultsDomain = ref<string | null>(entry.verificationResultsDomain ?? null);

const currentStep = ref(queuedDomain ? 2 : initialDomain ? 1 : 0);
const customDomain = ref<string | null>(queuedDomain ?? resultsDomain.value ?? initialDomain);
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

const onVerify = (provider: string) => {
  dnsProvider.value = provider;
  currentStep.value = 2;
};

const onResultsQueued = () => {
  resultsDomain.value = null;
  currentStep.value = 2;
};

const onSelectDifferentProvider = () => {
  resultsDomain.value = null;
  currentStep.value = 1;
};

const onAddAliases = () => {
  // Email aliases are managed from the email settings
  router.push('/settings');
};

const onDone = () => {
  requestCustomDomainsExpanded();
  router.push('/settings');
};
</script>

<script lang="ts">
export default {
  name: 'CustomDomainsView',
};
</script>

<template>
  <card-container>
    <verification-results-view
      v-if="resultsDomain"
      :domain-name="resultsDomain"
      @queued="onResultsQueued"
      @select-provider="onSelectDifferentProvider"
      @done="onDone"
      @add-aliases="onAddAliases"
    />

    <template v-else>
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
        @verify="onVerify"
      />
      <step3-summary v-else-if="currentStep === 2 && customDomain" :domain-name="customDomain" @done="onDone" />
    </template>
  </card-container>
</template>

<style scoped>
.steps {
  margin-block-end: 2rem;
}
</style>
