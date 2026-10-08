<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes, PrimaryButton, SelectInput } from '@thunderbirdops/services-ui';
import { PhCaretDown, PhCaretRight } from '@phosphor-icons/vue';
import DnsRecordsTable from './DnsRecordsTable.vue';
import { getDnsProviders, getRemoteDNSRecords, verifyDomain } from '../api';
import type { DNSRecord } from '../types';

const { t } = useI18n();

const props = defineProps<{
  domainName: string;
}>();

const emit = defineEmits<{
  cancel: [];
  verify: [provider: string];
}>();

const ICANN_LOOKUP_URL = 'https://lookup.icann.org/';

const providers = computed(() => [
  { label: t('views.customDomains.stepIdentify.dnsProviderPlaceholder'), value: '' },
  ...getDnsProviders(),
]);
const selectedProvider = ref<string>('');
const selectedProviderLabel = computed(
  () => providers.value.find((provider) => provider.value === selectedProvider.value)?.label ?? ''
);

const records = ref<DNSRecord[] | null>(null);
const error = ref<string | null>(null);
const isLoadingRecords = ref(false);
const showRecords = ref(true);
const isVerifying = ref(false);

const onContinue = async () => {
  if (!selectedProvider.value || isLoadingRecords.value) {
    return;
  }

  isLoadingRecords.value = true;
  error.value = null;

  try {
    const data = await getRemoteDNSRecords(props.domainName);

    if (data.success) {
      records.value = data.dns_records ?? [];
    } else {
      console.error(data.error);
      error.value = data.error ?? '';
    }
  } catch (e) {
    console.error(e);
    error.value = String(e);
  } finally {
    isLoadingRecords.value = false;
  }
};

const onVerify = async () => {
  if (isVerifying.value) {
    return;
  }

  isVerifying.value = true;
  error.value = null;

  try {
    const data = await verifyDomain(props.domainName);

    // Transient mail-backend outage! Stay on this step so the user can try again
    if (data.code === 'mail_backend_unavailable') {
      error.value = t('views.mail.sections.customDomains.mailBackendUnavailable');
      return;
    }

    // The summary step only says verification is in progress, so the result itself isn't needed here
    emit('verify', selectedProvider.value);
  } catch (e) {
    console.error(e);
    error.value = String(e);
  } finally {
    isVerifying.value = false;
  }
};
</script>

<template>
  <section class="step-identify">
    <h2>{{ t('views.customDomains.stepIdentify.title', { domain: `[${domainName}]` }) }}</h2>
    <p class="description">{{ t('views.customDomains.stepIdentify.description') }}</p>

    <form @submit.prevent="onContinue">
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

      <notice-bar v-if="error && !records" :type="NoticeBarTypes.Critical" class="error-notice">
        <span>{{ error }}</span>
      </notice-bar>

      <div v-if="!records" class="actions">
        <primary-button form-action="none" variant="outline" @click="emit('cancel')">
          {{ t('views.customDomains.stepIdentify.cancel') }}
        </primary-button>
        <primary-button form-action="submit" :disabled="!selectedProvider || isLoadingRecords">
          {{ t('views.customDomains.stepIdentify.continue') }}
        </primary-button>
      </div>
    </form>

    <div v-if="records" class="update-records">
      <h3>{{ t('views.customDomains.stepIdentify.updateRecordsTitle') }}</h3>
      <p class="description">
        {{ t('views.customDomains.stepIdentify.updateRecordsDescription', { provider: selectedProviderLabel }) }}
      </p>

      <button
        type="button"
        class="records-toggle"
        :aria-expanded="showRecords"
        aria-controls="dns-records"
        @click="showRecords = !showRecords"
      >
        <ph-caret-down v-if="showRecords" size="20" aria-hidden="true" />
        <ph-caret-right v-else size="20" aria-hidden="true" />
        <span>{{ t('views.customDomains.stepIdentify.checkRecordFormat') }}</span>
      </button>

      <div v-show="showRecords" id="dns-records">
        <h4>{{ t('views.customDomains.stepIdentify.dnsRecords') }}</h4>
        <dns-records-table :records="records" />
      </div>

      <notice-bar v-if="error" :type="NoticeBarTypes.Critical" class="error-notice records-error">
        <span>{{ error }}</span>
      </notice-bar>

      <div class="actions">
        <primary-button form-action="none" variant="outline" @click="emit('cancel')">
          {{ t('views.customDomains.stepIdentify.cancel') }}
        </primary-button>
        <primary-button form-action="none" :disabled="isVerifying" @click="onVerify">
          {{ t('views.customDomains.stepIdentify.verifyDnsSettings') }}
        </primary-button>
      </div>
    </div>

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

  .error-notice {
    margin-block-end: 1.5rem;

    &.records-error {
      margin-block-start: 1.5rem;
    }
  }

  .update-records {
    h3 {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--colour-ti-secondary);
      margin-block-end: 0.5rem;
    }

    h4 {
      font-size: 1rem;
      font-weight: 600;
      color: var(--colour-ti-secondary);
      margin-block: 1.5rem 1rem;
    }

    .records-toggle {
      all: unset;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      width: 100%;
      padding: 0.75rem 1rem;
      border: 1px solid var(--colour-neutral-border);
      border-radius: 0.5rem;
      font-family: metropolis;
      font-size: 1rem;
      font-weight: 600;
      color: var(--colour-ti-secondary);
      cursor: pointer;

      &:hover {
        background-color: var(--colour-neutral-lower);
      }

      &:focus-visible {
        outline: 2px solid var(--colour-primary-default);
        outline-offset: 2px;
      }
    }
  }

  .actions {
    margin-block-start: 1.5rem;
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
