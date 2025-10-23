<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhX } from '@phosphor-icons/vue';

enum STEP {
  INITIAL = 'initial',
  ADD = 'add',
  VERIFY_DOMAIN = 'verify',
}

const { t } = useI18n();

const step = ref<STEP>(STEP.INITIAL);
const customDomain = ref(null);
const showNoticeBar = ref(true);

const recordsInfo = [
  {
    type: 'MX',
    name: '@',
    value: 'mail.thundermail.com',
    priority: 10,
  },
  {
    type: 'TXT',
    name: '_dmarc',
    value: 'v=spf1 include:thundermail.com ~all',
    priority: '-',
  },
  {
    type: 'SRV',
    name: '_autodiscover._tcp',
    value: '0 0 443 autodiscover.thundermail.com',
    priority: '-',
  },
]

const onVerifyDomain = () => {
  // TODO: Make API call to save the domain for verification
  step.value = STEP.INITIAL;
};
</script>

<template>
  <template v-if="step === STEP.INITIAL">
    <primary-button variant="outline" @click="step = STEP.ADD">{{ t('views.mail.sections.customDomains.addDomain') }}</primary-button>
  </template>
  <template v-else-if="step === STEP.ADD">
    <text-input
      :placeholder="t('views.mail.sections.customDomains.domainPlaceholder')"
      name="custom-domain"
      :help="t('views.mail.sections.customDomains.domainHelp')"
      class="custom-domain-text-input"
      v-model="customDomain"
    >
      {{ t('views.mail.sections.customDomains.enterCustomDomain') }}
    </text-input>

    <primary-button variant="outline" @click="step = STEP.VERIFY_DOMAIN">{{ t('views.mail.sections.customDomains.continue') }}</primary-button>
  </template>
  <template v-else-if="step === STEP.VERIFY_DOMAIN">
    <h3>{{ t('views.mail.sections.customDomains.verifyStepTitle') }}</h3>
    <div class="verify-step-list">
      <p>{{ t('views.mail.sections.customDomains.verifyStepOne') }}</p>
      <p>{{ t('views.mail.sections.customDomains.verifyStepTwo') }}</p>
      <p>{{ t('views.mail.sections.customDomains.verifyStepThree') }}</p>
      <p class="verify-step-note">{{ t('views.mail.sections.customDomains.verifyStepNote') }}</p>
    </div>

    <div class="records-table-wrapper">
      <div class="records-table-header">
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderType') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderNameHost') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderValueData') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderPriority') }}</p>
      </div>
      <div class="records-table-row" v-for="record in recordsInfo" :key="record.value">
        <p>{{ record.type }}</p>
        <p>{{ record.name }}</p>
        <p>{{ record.value }}</p>
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

    <primary-button class="verify-step-button" @click="onVerifyDomain">{{ t('views.mail.sections.customDomains.verifyStepButton') }}</primary-button>
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
  gap: 1.5rem;
  line-height: 1.32;
  color: var(--colour-ti-secondary);
  margin-block-end: 1.5rem;

  .verify-step-note {
    font-size: 0.875rem;
    line-height: normal;
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