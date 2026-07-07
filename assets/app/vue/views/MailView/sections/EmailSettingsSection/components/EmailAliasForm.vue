<script setup lang="ts">
import { ref, computed, useTemplateRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { TextInput, SelectInput, PrimaryButton, LinkButton } from '@thunderbirdops/services-ui';
import { EMAIL_ALIASES_SUPPORT_URL, EMAIL_ALIASES_CATCH_ALL_SUPPORT_URL } from '@/defines';

// Types
import { EMAIL_ALIAS_STEP } from '../types';
import { validateEmailAlias } from './emailAliasValidation';

const { t } = useI18n();

const props = defineProps<{
  allDomainOptions: string[];
  existingCatchAlls: string[];
  showSharedDomains: boolean;
}>();

const emit = defineEmits<{
  'add-alias': [emailAlias: string, domain: string];
}>();

// And the domains in the settings.ALLOWED_EMAIL_DOMAINS from the backend
const allowedDomains = window._page.allowedDomains || [];

const step = ref<EMAIL_ALIAS_STEP>(EMAIL_ALIAS_STEP.INITIAL);
const emailAlias = ref<string>('');
const selectedDomain = ref(props.allDomainOptions[0] ?? null);
const formRef = useTemplateRef('formRef');
const validationError = ref<string | null>(null);
const customDomainSelected = computed(() => !allowedDomains.includes(selectedDomain.value));

const allDomainOptions = computed(() => props.allDomainOptions.map((domain) => ({
  label: domain,
  value: domain,
})).filter(
  (domain) => props.showSharedDomains && allowedDomains.includes(domain.value)
  || !allowedDomains.includes(domain.value)
));

/**
 * Returns the next to be filled in for name's help section.
 *
 * If you're able to make a catch-all alias a second line will appear with information.
 */
const nameHelp = computed(() => {
  const hasCatchAll = props.existingCatchAlls.some((catchAll) => catchAll.endsWith(`@${selectedDomain.value}`));

  if (customDomainSelected.value && !hasCatchAll) {
    return `${t('views.mail.sections.emailSettings.nameHelp')}\n\n${t('views.mail.sections.emailSettings.nameCatchAllHelp')}`;
  }
  return t('views.mail.sections.emailSettings.nameHelp');
});

const onEmailAliasInput = () => {
  const messageKey = validateEmailAlias({
    value: emailAlias.value,
    selectedDomain: selectedDomain.value,
    allowedDomains,
    existingCatchAlls: props.existingCatchAlls,
  });

  validationError.value = messageKey ? t(messageKey) : null;
};

const onSubmit = () => {
  onEmailAliasInput();

  if (!validationError.value && formRef.value.checkValidity()) {
    emit('add-alias', emailAlias.value, selectedDomain.value);
    emailAlias.value = '';
    selectedDomain.value = props.allDomainOptions[0] ?? null;
    validationError.value = null;
    step.value = EMAIL_ALIAS_STEP.INITIAL;
  }
};

// Validate on selected domain change as well
watch(selectedDomain, () => {
  // Retain behaviour of not testing empty strings on domain change for now.
  if (emailAlias.value === '') {
    return;
  }
  onEmailAliasInput();
});
</script>

<template>
  <template v-if="step === EMAIL_ALIAS_STEP.INITIAL">
    <primary-button
      variant="outline"
      class="add-email-alias-button"
      @click="step = EMAIL_ALIAS_STEP.SUBMIT"
    >
      {{ t('views.mail.sections.emailSettings.addEmailAlias') }}
    </primary-button>
  </template>

  <template v-else-if="step === EMAIL_ALIAS_STEP.SUBMIT">
    <form @submit.prevent="onSubmit" ref="formRef">
      <div class="email-alias-input-wrapper">
        <text-input
          name="email-alias"
          v-model="emailAlias"
          @input="onEmailAliasInput"
          :help="nameHelp"
          :error="validationError"
        >
          {{ t('views.mail.sections.emailSettings.name') }}
        </text-input>
        <span>@</span>
        <select-input name="domain" :options="allDomainOptions" v-model="selectedDomain" required>
          {{ t('views.mail.sections.emailSettings.domain') }}
        </select-input>
      </div>

      <div class="email-alias-form-buttons">
        <primary-button @click="onSubmit">
          {{ t('views.mail.sections.emailSettings.submit') }}
        </primary-button>
        <link-button @click="step = EMAIL_ALIAS_STEP.INITIAL">
          {{ t('views.mail.sections.emailSettings.cancel') }}
        </link-button>
      </div>
    </form>
  </template>

  <i18n-t keypath="views.mail.sections.emailSettings.emailAliasSupportText" tag="p" class="email-alias-support-text">
    <template #emailAliasesSupportLink>
      <a :href="EMAIL_ALIASES_SUPPORT_URL" target="_blank" rel="noopener noreferrer">
        {{ t('views.mail.sections.emailSettings.emailAliasesArticleTitle') }}
      </a>
    </template>
    <template #emailAliasesCatchAllSupportLink>
      <a :href="EMAIL_ALIASES_CATCH_ALL_SUPPORT_URL" target="_blank" rel="noopener noreferrer">
        {{ t('views.mail.sections.emailSettings.emailAliasesCatchAllArticleTitle') }}
      </a>
    </template>
  </i18n-t>
</template>

<style scoped>
:deep(.tooltip) {
  min-width: 200px;
}

:deep(.email-alias-input-wrapper .help-label) {
  white-space: break-spaces;
}

.email-alias-input-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-block-end: 1.5rem;
  max-width: 80%;

  span {
    margin-block-start: 2.425rem;
  }

  & > :first-child {
    width: 60%;
  }

  & > :last-child {
    width: 40%;
  }
}

.notice-bar-error {
  margin-block-end: 1.5rem;
}

.email-alias-form-buttons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.email-alias-support-text {
  font-size: 0.75rem;
  margin-block-start: 1rem;

  a {
    color: var(--colour-ti-highlight);
  }
}
</style>
