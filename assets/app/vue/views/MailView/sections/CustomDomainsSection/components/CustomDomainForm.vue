<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhX } from '@phosphor-icons/vue';

// Types
import { CustomDomain, DNSRecord, STEP, DOMAIN_STATUS } from '../types';

// API
import { addCustomDomain, verifyDomain } from '../api';

// Utils
import { generateDNSRecords } from '../utils';

const { t } = useI18n();

const props = defineProps<{
  customDomains: CustomDomain[];
  lastDomainRemoved?: string;
}>();

const emit = defineEmits<{
  'step-change': [step: STEP]
  'custom-domain-added': [customDomain: string]
  'custom-domain-verified': [customDomain: { name: string, status: DOMAIN_STATUS }]
}>();

const step = ref<STEP>(STEP.INITIAL);
const customDomain = ref(null);
const showNoticeBar = ref(true);
const isAddingCustomDomain = ref(false);
const isVerifyingDomain = ref(false);
const customDomainError = ref<string>(null);

// TODO: Remove this once we know what a verified verification status looks like
const verificationStatus = ref<Record<string, any>>(null);

const maxCustomDomains = window._page?.maxCustomDomains;

const recordsInfo = ref<DNSRecord[]>([]);

const onCreateCustomDomain = async () => {
  if (props.customDomains.some((domain) => domain.name === customDomain.value)) {
    customDomainError.value = t('views.mail.sections.customDomains.domainAlreadyExists');
    return;
  }

  isAddingCustomDomain.value = true;

  try {
    const data = await addCustomDomain(customDomain.value);

    if (data.success) {
      emit('custom-domain-added', customDomain.value);
      recordsInfo.value = await generateDNSRecords(customDomain.value);
      step.value = STEP.VERIFY_DOMAIN;
    } else {
      console.error(data.error);
      customDomainError.value = data.error;
    }
  } catch (error) {
    console.error(error);
    customDomainError.value = error;
  } finally {
    isAddingCustomDomain.value = false;
  }
};

const onVerifyDomain = async () => {
  isVerifyingDomain.value = true;

  try {
    const data = await verifyDomain(customDomain.value);

    // TODO: Remove this once we know what a verified verification status looks like
    verificationStatus.value = data.verification_status;

    if (data.success) {
      emit('custom-domain-verified', { name: customDomain.value, status: DOMAIN_STATUS.VERIFIED });
      step.value = STEP.INITIAL;
      customDomainError.value = null;
    } else {
      emit('custom-domain-verified', { name: customDomain.value, status: DOMAIN_STATUS.FAILED });
    }
  } catch (error) {
    emit('custom-domain-verified', { name: customDomain.value, status: DOMAIN_STATUS.FAILED });
    console.error(error);
  } finally {
    isVerifyingDomain.value = false;
    customDomain.value = null;
  }
};

const viewDnsRecords = async (domainName: string) => {
  customDomain.value = domainName;
  recordsInfo.value = await generateDNSRecords(domainName);
  step.value = STEP.VERIFY_DOMAIN;
};

defineExpose({
  viewDnsRecords
});

watch(step, (newStep) => {
  emit('step-change', newStep);
}, { immediate: true });

watch(() => props.lastDomainRemoved, (newLastDomainRemoved) => {
  // If we just removed the domain we were adding, reset the step to initial
  if (newLastDomainRemoved === customDomain.value) {
    step.value = STEP.INITIAL;
    customDomain.value = null;
    customDomainError.value = null;
  }
}, { immediate: true });
</script>

<template>
  <template v-if="step === STEP.INITIAL">
    <primary-button
      variant="outline"
      @click="step = STEP.ADD"
      v-if="customDomains.length < maxCustomDomains"
    >
      {{ t('views.mail.sections.customDomains.addDomain') }}
    </primary-button>
  </template>

  <template v-else-if="step === STEP.ADD">
    <text-input
      :placeholder="t('views.mail.sections.customDomains.domainPlaceholder')"
      name="custom-domain"
      :help="t('views.mail.sections.customDomains.domainHelp')"
      :error="customDomainError"
      class="custom-domain-text-input"
      v-model="customDomain"
    >
      {{ t('views.mail.sections.customDomains.enterCustomDomain') }}
    </text-input>

    <primary-button variant="outline" @click="onCreateCustomDomain" :disabled="isAddingCustomDomain">
      {{ t('views.mail.sections.customDomains.continue') }}
    </primary-button>
  </template>

  <template v-else-if="step === STEP.VERIFY_DOMAIN">
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

    <div class="records-table-wrapper">
      <div class="records-table-header">
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderType') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderNameHost') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderValueData') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderPriority') }}</p>
      </div>
      <div class="records-table-row" v-for="record in recordsInfo" :key="`${record.type}-${record.name}-${record.content}`">
        <p>{{ record.type }}</p>
        <p>{{ record.name }}</p>
        <p>{{ record.content }}</p>
        <p>{{ record.priority }}</p>
      </div>
    </div>

    <notice-bar :type="NoticeBarTypes.Info" class="verify-step-notice-bar" v-if="showNoticeBar">
      <strong>{{ t('views.mail.sections.customDomains.verifyStepInfoTitle') }}</strong>
      <p>{{ t('views.mail.sections.customDomains.verifyStepInfoDescription') }}</p>

      <template #cta>
        <button class="close-button" @click="showNoticeBar = false">
          <ph-x size="24" />
        </button>
      </template>
    </notice-bar>

    <!-- TODO: Remove this once we know what a verified verification status looks like -->
    <notice-bar :type="NoticeBarTypes.Warning" class="verify-step-notice-bar" v-if="verificationStatus">
      <template v-for="status in verificationStatus" :key="status.type">
        <p>{{ JSON.stringify(status) }}</p>
      </template>
    </notice-bar>

    <primary-button
      class="verify-step-button"
      @click="onVerifyDomain"
      :disabled="isVerifyingDomain"
    >
      {{ t('views.mail.sections.customDomains.verifyStepButton') }}
    </primary-button>
  </template>
</template>

<style scoped>
.custom-domain-text-input {
  margin-block-end: 1.5rem;
}

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

    &:not(:first-of-type) {
      margin-inline-start: 1.25rem;
    }
  }

  .verify-step-note {
    font-size: 0.875rem;
    line-height: normal;
    margin: 0;
  }
}

.records-table-wrapper {
  overflow-x: auto;
  margin-block-end: 1.5rem;
}

.records-table-header {
  display: flex;
  align-items: center;
  border-block-end: 1px solid var(--colour-neutral-border);
  min-width: max-content;

  p {
    padding: 1rem;
    text-transform: uppercase;
    width: 150px;
    flex-shrink: 0;
    font-weight: 600;
    font-size: 0.8125rem;
    letter-spacing: 0.39px;
  }
}

.records-table-row {
  display: flex;
  align-items: center;
  min-width: max-content;

  p {
    padding: 1rem;
    font-size: 0.75rem;
    width: 150px;
    flex-shrink: 0;
    word-break: break-word;
  }

  &:nth-child(odd) {
    background-color: var(--colour-neutral-lower);
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

@media (min-width: 768px) {
  .custom-domain-text-input {
    max-width: 50%;
  }

  .records-table-wrapper {
    overflow-x: visible;
  }

  .records-table-header {
    min-width: auto;

    p {
      width: 25%;
      flex: 1;
    }
  }

  .records-table-row {
    min-width: auto;

    p {
      width: 25%;
      flex: 1;
    }
  }
}
</style>