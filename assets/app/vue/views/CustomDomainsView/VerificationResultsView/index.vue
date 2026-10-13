<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { BaseBadge, BaseBadgeTypes, CheckboxInput, NoticeBar, NoticeBarTypes, PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import DnsFormatPanel from '../components/DnsFormatPanel.vue';
import DnsRecordsTable from '../components/DnsRecordsTable.vue';
import VerifiedRecordTypesTable from '../components/VerifiedRecordTypesTable.vue';
import { verifyDomain } from '../api';
import { buildResultRecords } from './utils';
import type { VerificationApiResult } from './types';
import type { DNSRecord } from '../types';

const { t, te } = useI18n();
const route = useRoute();
const router = useRouter();

const domainName = computed(() => (typeof route.query.domain === 'string' ? route.query.domain : ''));

const isVerifying = ref(false);
const isVerified = ref(false);
const error = ref<string | null>(null);
const records = ref<DNSRecord[]>([]);
const validationErrors = ref<string[]>([]);
const notifyByEmail = ref(false);
const recordsTableRef = ref<InstanceType<typeof DnsRecordsTable> | null>(null);

const hasRecordIssues = computed(() => records.value.some((record) => record.issue));

const formatValidationError = (key: string): string => {
  const translationKey = `views.mail.sections.customDomains.verificationValidationErrors.${key}`;
  return te(translationKey) ? t(translationKey) : key;
};

const verify = async () => {
  if (isVerifying.value) {
    return;
  }

  isVerifying.value = true;
  error.value = null;

  try {
    const data: VerificationApiResult = await verifyDomain(domainName.value);

    // Transient mail-backend outage: keep whatever we were showing and let the user retry
    if (data.code === 'mail_backend_unavailable') {
      error.value = t('views.mail.sections.customDomains.mailBackendUnavailable');
      return;
    }

    isVerified.value = !!data.success;
    records.value = buildResultRecords(data, t);
    validationErrors.value = [...(data.critical_errors ?? []), ...(data.warnings ?? [])];
  } catch (e) {
    console.error(e);
    error.value = String(e);
  } finally {
    isVerifying.value = false;
  }
};

const onSelectDifferentProvider = () => {
  router.push({ path: '/custom-domains', query: { domain: domainName.value } });
};

const onAddAliases = () => {
  // Email aliases are managed from the email settings
  router.push('/settings');
};

const onFinishLater = () => {
  // TODO: persist the "send email notification when verification is complete" preference
  router.push('/settings');
};

onMounted(() => {
  if (!domainName.value) {
    router.replace('/settings');
    return;
  }

  verify();
});
</script>

<script lang="ts">
export default {
  name: 'VerificationResultsView',
};
</script>

<template>
  <card-container>
    <section class="verification-results">
      <div class="title-row">
        <h2>{{ t('views.customDomains.verificationResults.title', { domain: domainName }) }}</h2>
        <base-badge v-if="isVerified" :type="BaseBadgeTypes.Verified">
          {{ t('views.mail.sections.customDomains.verified') }}
        </base-badge>
      </div>

      <notice-bar v-if="error" :type="NoticeBarTypes.Critical" class="banner">
        <span>{{ error }}</span>
      </notice-bar>

      <output v-if="isVerifying && records.length === 0" class="description">
        {{ t('views.customDomains.verificationResults.verifying') }}
      </output>

      <template v-else-if="isVerified">
        <p class="description">{{ t('views.customDomains.verificationResults.successDescription') }}</p>

        <div class="actions">
          <primary-button form-action="none" variant="outline" @click="onFinishLater">
            {{ t('views.customDomains.verificationResults.done') }}
          </primary-button>
          <primary-button form-action="none" @click="onAddAliases">
            {{ t('views.customDomains.verificationResults.addAliases') }}
          </primary-button>
        </div>

        <verified-record-types-table :records="records" />
      </template>

      <template v-else>
        <template v-if="records.length > 0 || validationErrors.length > 0">
          <notice-bar :type="NoticeBarTypes.Critical" class="banner">
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

          <h3>{{ t('views.customDomains.verificationResults.updateRecordsTitle') }}</h3>
          <p class="description">{{ t('views.customDomains.verificationResults.updateRecordsDescription') }}</p>

          <i18n-t keypath="views.customDomains.verificationResults.notRightProvider" tag="p" class="provider-hint">
            <template #link>
              <a href="#" @click.prevent="onSelectDifferentProvider">
                {{ t('views.customDomains.verificationResults.selectDifferentProvider') }}
              </a>
            </template>
          </i18n-t>

          <dns-format-panel />

          <h4>{{ t('views.customDomains.stepIdentify.dnsRecords') }}</h4>
          <dns-records-table ref="recordsTableRef" :records="records" />
        </template>

        <checkbox-input
          v-model="notifyByEmail"
          name="notify-by-email"
          class="notify"
          :label="t('views.customDomains.verificationResults.notifyByEmail')"
        />

        <div class="actions">
          <primary-button form-action="none" variant="outline" @click="onFinishLater">
            {{ t('views.customDomains.verificationResults.finishLater') }}
          </primary-button>
          <primary-button form-action="none" :disabled="isVerifying" @click="verify">
            {{ t('views.customDomains.verificationResults.retryVerification') }}
          </primary-button>
        </div>

        <router-link to="/contact" class="help-link">
          {{ t('views.customDomains.stepAdd.needHelp') }}
        </router-link>
      </template>
    </section>
  </card-container>
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

@media (min-width: 768px) {
  .verification-results .description {
    max-width: 50%;
  }
}
</style>
