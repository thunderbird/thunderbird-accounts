<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { BaseBadge, BaseBadgeTypes, NoticeBar, NoticeBarTypes, PrimaryButton } from '@thunderbirdops/services-ui';
import DnsFormatPanel from '../components/DnsFormatPanel.vue';
import DnsRecordsTable from '../components/DnsRecordsTable.vue';
import VerifiedRecordTypesTable from '../components/VerifiedRecordTypesTable.vue';
import { getRemoteDNSRecords, getVerificationResult, verifyDomain } from '../api';
import { buildResultRecords } from './utils';
import type { VerificationApiResult } from './types';
import { DNS_PROVIDERS, GENERIC_DNS_PROVIDER_ID } from '../dnsProviders';
import type { DNSRecord } from '../types';

const { t, te } = useI18n();

const props = defineProps<{
  domainName: string;
}>();

const emit = defineEmits<{
  // Verification was queued, the summary takes it from here
  queued: [];
  selectProvider: [];
  done: [];
  addAliases: [];
}>();

const isLoading = ref(true);
const isVerifying = ref(false);
const isVerified = ref(false);
const isFailed = ref(false);
const hasBeenVerified = ref(false);
const dnsProvider = ref<string | null>(null);

// "Other" reads oddly in "Sign in to Other", so it falls back to a generic phrase
const providerLabel = computed(() => {
  if (!dnsProvider.value) {
    return '';
  }
  return dnsProvider.value === GENERIC_DNS_PROVIDER_ID
    ? t('views.customDomains.stepIdentify.genericProviderName')
    : (DNS_PROVIDERS.find((provider) => provider.id === dnsProvider.value)?.label ?? '');
});
const error = ref<string | null>(null);
const records = ref<DNSRecord[]>([]);
const validationErrors = ref<string[]>([]);
const recordsTableRef = ref<InstanceType<typeof DnsRecordsTable> | null>(null);

const hasRecordIssues = computed(() => records.value.some((record) => record.issue));

const formatValidationError = (key: string): string => {
  const translationKey = `views.mail.sections.customDomains.verificationValidationErrors.${key}`;
  return te(translationKey) ? t(translationKey) : key;
};

// Verification runs in the background, so what is shown is the outcome of the last attempt
const load = async () => {
  try {
    const data: VerificationApiResult & { status?: string; dns_provider?: string } = await getVerificationResult(props.domainName);

    if (!data.success) {
      error.value = (data as { error?: string }).error ?? null;
      return;
    }

    isVerified.value = data.status === 'verified';
    isFailed.value = data.status === 'failed';
    dnsProvider.value = data.dns_provider || null;
    records.value = buildResultRecords(data, t);
    hasBeenVerified.value = records.value.length > 0;
    validationErrors.value = [...(data.critical_errors ?? []), ...(data.warnings ?? [])];

    // Nothing was checked yet (or before results were kept), so show the records the domain needs
    if (records.value.length === 0) {
      const expected = await getRemoteDNSRecords(props.domainName);
      records.value = expected.success ? buildResultRecords(expected, t) : [];
    }
  } catch (e) {
    console.error(e);
    error.value = String(e);
  } finally {
    isLoading.value = false;
  }
};

const retry = async () => {
  if (isVerifying.value) {
    return;
  }

  isVerifying.value = true;
  error.value = null;

  try {
    const data = await verifyDomain(props.domainName);

    // Transient mail-backend outage: keep what we were showing and let the user retry
    if (data.code === 'mail_backend_unavailable') {
      error.value = t('views.mail.sections.customDomains.mailBackendUnavailable');
      return;
    }

    if (!data.success) {
      error.value = data.error;
      return;
    }

    emit('queued');
  } catch (e) {
    console.error(e);
    error.value = String(e);
  } finally {
    isVerifying.value = false;
  }
};

onMounted(load);
</script>

<script lang="ts">
export default {
  name: 'VerificationResultsView',
};
</script>

<template>
  <section class="verification-results">
    <div class="title-row">
      <!-- Held back until loaded, so the title doesn't flip once it is known whether anything was verified -->
      <h2 v-if="!isLoading">
        {{
          hasBeenVerified
            ? t('views.customDomains.verificationResults.title', { domain: domainName })
            : t('views.customDomains.verificationResults.updateRecordsTitle')
        }}
      </h2>
      <base-badge v-if="isVerified" :type="BaseBadgeTypes.Verified">
        {{ t('views.mail.sections.customDomains.verified') }}
      </base-badge>
    </div>

    <notice-bar v-if="error" :type="NoticeBarTypes.Critical" class="banner">
      <span>{{ error }}</span>
    </notice-bar>

    <output v-if="isLoading" class="description">
      {{ t('views.customDomains.verificationResults.loading') }}
    </output>

    <template v-else-if="isVerified">
      <p class="description">{{ t('views.customDomains.verificationResults.successDescription') }}</p>

      <div class="actions">
        <primary-button form-action="none" variant="outline" @click="emit('done')">
          {{ t('views.customDomains.verificationResults.done') }}
        </primary-button>
        <primary-button form-action="none" @click="emit('addAliases')">
          {{ t('views.customDomains.verificationResults.addAliases') }}
        </primary-button>
      </div>

      <verified-record-types-table :records="records" />
    </template>

    <template v-else>
      <template v-if="records.length > 0 || validationErrors.length > 0">
        <notice-bar v-if="isFailed" :type="NoticeBarTypes.Critical" class="banner">
          <strong>{{ t('views.customDomains.verificationResults.failedTitle') }}</strong>
          {{ t('views.customDomains.verificationResults.failedDescription') }}

          <!-- Without any flagged record the specific reasons are the only feedback -->
          <ul v-if="!hasRecordIssues && validationErrors.length > 0">
            <li v-for="key in validationErrors" :key="key">{{ formatValidationError(key) }}</li>
          </ul>

          <template v-if="hasRecordIssues" #cta>
            <button type="button" class="first-error-link" @click="recordsTableRef?.scrollToFirstIssue()">
              {{ t('views.customDomains.verificationResults.goToFirstError') }}
            </button>
          </template>
        </notice-bar>

        <h3 v-if="hasBeenVerified">{{ t('views.customDomains.verificationResults.updateRecordsTitle') }}</h3>
        <p class="description">
          {{
            providerLabel
              ? t('views.customDomains.verificationResults.updateRecordsDescriptionProvider', { provider: providerLabel })
              : t('views.customDomains.verificationResults.updateRecordsDescription')
          }}
        </p>

        <i18n-t keypath="views.customDomains.verificationResults.notRightProvider" tag="p" class="provider-hint">
          <template #link>
            <a href="#" @click.prevent="emit('selectProvider')">
              {{ t('views.customDomains.verificationResults.selectDifferentProvider') }}
            </a>
          </template>
        </i18n-t>

        <dns-format-panel />

        <h4>{{ t('views.customDomains.stepIdentify.dnsRecords') }}</h4>
        <dns-records-table ref="recordsTableRef" :records="records" />
      </template>

      <div class="actions">
        <primary-button form-action="none" variant="outline" @click="emit('done')">
          {{ t('views.customDomains.verificationResults.finishLater') }}
        </primary-button>
        <primary-button form-action="none" :disabled="isVerifying" @click="retry">
          {{ t('views.customDomains.verificationResults.retryVerification') }}
        </primary-button>
      </div>

      <router-link to="/contact" class="help-link">
        {{ t('views.customDomains.stepAdd.needHelp') }}
      </router-link>
    </template>
  </section>
</template>

<style scoped>
.verification-results {
  .title-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
    margin-block-end: 1.5rem;
  }

  h2 {
    font-family: metropolis, sans-serif;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--colour-ti-highlight);
    margin: 0;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--colour-ti-secondary);
    margin-block: 1.5rem 0.5rem;
  }

  h4 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--colour-ti-secondary);
    margin-block: 1.5rem 1rem;
  }

  .description {
    display: block;
    font-size: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
    margin-block-end: 1.5rem;
  }

  .provider-hint {
    font-size: 0.875rem;
    color: var(--colour-ti-secondary);
    margin-block-end: 1.5rem;

    a {
      color: var(--colour-primary-default);
    }
  }

  .banner {
    margin-block-end: 1.5rem;

    ul {
      margin: 0.5rem 0 0;
      padding-inline-start: 1.25rem;
    }
  }

  .first-error-link {
    all: unset;
    font-size: 0.8125rem;
    text-decoration: underline;
    color: var(--colour-ti-secondary);
    cursor: pointer;
    white-space: nowrap;
  }

  .notify {
    margin-block: 1.5rem;
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
</style>
