<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';

import { DecoratedDnsTableRow, InlineIssue, RecordTab } from '../types';
import DnsRecordsTable from './DnsRecordsTable.vue';

const props = defineProps<{
  domainName: string;
  dnsTableRows: DecoratedDnsTableRow[];
  unanchoredValidationIssues: InlineIssue[];
  isVerifyingDomain: boolean;
  showRecordStatus: boolean;
}>();

const emit = defineEmits<{
  verify: [];
}>();

const { t } = useI18n();

const activeTab = ref<RecordTab>(RecordTab.CONFLICTING);

const hasConflictingRecords = computed(() => {
  return props.dnsTableRows.some((row) => row.status === 'warning' || row.status === 'critical');
})

const onTabSelected = (tab: RecordTab) => {
  activeTab.value = tab;
};
</script>

<template>
  <h3>{{ t('views.mail.sections.customDomains.verifyStepTitle') }}</h3>
  <div class="verify-step-list">
    <h4>{{ t('views.mail.sections.customDomains.verifyStepOneTitle') }}</h4>
    <p>{{ t('views.mail.sections.customDomains.verifyStepOne') }}</p>
    <h4>{{ t('views.mail.sections.customDomains.verifyStepTwoTitle') }}</h4>
    <p>{{ t('views.mail.sections.customDomains.verifyStepTwo') }}</p>
    <h4>{{ t('views.mail.sections.customDomains.verifyStepThreeTitle') }}</h4>
    <p>{{ t('views.mail.sections.customDomains.verifyStepThree') }}</p>
    <p class="verify-step-note">
      <strong>{{ t('views.mail.sections.customDomains.verifyStepNoteTip') }}</strong>
      {{ t('views.mail.sections.customDomains.verifyStepNote') }}
    </p>
  </div>

  <h2 class="domain-title-header">{{ t('views.mail.sections.customDomains.domains') }} > {{ t('views.mail.sections.customDomains.ownerDNSRecords', { domainName }) }}</h2>

  <div class="record-tabs" v-if="showRecordStatus && hasConflictingRecords">
    <button
      type="button"
      :class="{ active: activeTab === RecordTab.CONFLICTING }"
      @click="onTabSelected(RecordTab.CONFLICTING)"
    >
      {{ t('views.mail.sections.customDomains.conflictingRecords') }}
    </button>
    <button
      type="button"
      :class="{ active: activeTab === RecordTab.ALL }"
      @click="onTabSelected(RecordTab.ALL)"
    >
      {{ t('views.mail.sections.customDomains.allRecords') }}
    </button>
  </div>

  <dns-records-table
    :rows="dnsTableRows"
    :unanchored-validation-issues="unanchoredValidationIssues"
    :show-record-status="showRecordStatus"
    :active-tab="activeTab"
    :has-conflicting-records="hasConflictingRecords"
  />

  <!-- TODO: Uncomment this once we have the task / job to automatically verify domains -->
  <!-- <notice-bar :type="NoticeBarTypes.Info" class="verify-step-notice-bar" v-if="showNoticeBar">
    <strong>{{ t('views.mail.sections.customDomains.verifyStepInfoTitle') }}</strong>
    <p>{{ t('views.mail.sections.customDomains.verifyStepInfoDescription') }}</p>

    <template #cta>
      <button class="close-button" @click="showNoticeBar = false">
        <ph-x size="24" />
      </button>
    </template>
  </notice-bar> -->

  <primary-button class="verify-step-button" @click="emit('verify')" :disabled="isVerifyingDomain">
    {{ t('views.mail.sections.customDomains.verifyStepButton') }}
  </primary-button>
</template>

<style scoped>
h2 {
  font-size: 1rem;
  font-weight: 500;
  font-family: metropolis;
  color: var(--colour-ti-highlight);
  margin-block-end: 1rem;
  text-transform: uppercase;
}

h3 {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.48px;
  margin-block-end: 1.5rem;
}

.record-tabs {
  border-block-end: 1px solid var(--colour-neutral-border-intense);

  button {
    padding: 1rem;
    background-color: var(--colour-neutral-base);
    text-transform: uppercase;
    font-weight: 600;
    font-size: 0.83rem;
    border: none;
    cursor: pointer;
    color: var(--colour-ti-secondary);
    border-block-end: 1.5px solid transparent;

    &:hover {
      background-color: var(--colour-neutral-lower);
    }

    &.active {
      color: var(--colour-ti-base);
      border-block-end-color: var(--colour-primary-default);
    }
  }
}

.verify-step-list {
  display: flex;
  flex-direction: column;
  line-height: 1.32;
  color: var(--colour-ti-secondary);
  margin-block-end: 2.5rem;

  h4 {
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.32;
    margin-block-end: 0.25rem;
  }

  p {
    margin-inline-start: 1rem;
    margin-block-end: 1.5rem;
    font-size: 0.875rem;
  }

  .verify-step-note {
    font-size: 0.875rem;
    line-height: normal;
    margin: 0;
  }
}

.verify-step-notice-bar {
  margin-block-end: 1.5rem;

  .close-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem;
    border: none;
    border-radius: 300px;
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05);
    background-color: rgba(0, 0, 0, 0.05);
    color: var(--colour-ti-secondary);
    cursor: pointer;

    &:hover {
      background-color: rgba(0, 0, 0, 0.1);
    }

    &:active {
      background-color: rgba(0, 0, 0, 0.2);
    }
  }
}

.verify-step-button {
  margin-block-start: 1.5rem;
}
</style>
