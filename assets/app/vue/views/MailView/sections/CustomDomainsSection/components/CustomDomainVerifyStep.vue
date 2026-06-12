<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';

import type { DecoratedDnsTableRow, InlineIssue } from '../types';
import DnsRecordsTable from './DnsRecordsTable.vue';

defineProps<{
  dnsTableRows: DecoratedDnsTableRow[];
  unanchoredValidationIssues: InlineIssue[];
  isVerifyingDomain: boolean;
  showRecordStatus: boolean;
}>();

const emit = defineEmits<{
  verify: [];
}>();

const { t } = useI18n();
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

  <dns-records-table
    :rows="dnsTableRows"
    :unanchored-validation-issues="unanchoredValidationIssues"
    :show-record-status="showRecordStatus"
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
h3 {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.48px;
  margin-block-end: 1.5rem;
}

.verify-step-list {
  display: flex;
  flex-direction: column;
  line-height: 1.32;
  color: var(--colour-ti-secondary);
  margin-block-end: 1.5rem;

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
