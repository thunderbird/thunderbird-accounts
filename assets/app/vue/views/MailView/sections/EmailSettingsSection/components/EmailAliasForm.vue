<script setup lang="ts">
import { ref, computed, useTemplateRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { TextInput, SelectInput, PrimaryButton, LinkButton } from '@thunderbirdops/services-ui';

// Types
import { EMAIL_ALIAS_STEP } from '../types';

const { t } = useI18n();

const props = defineProps<{
  allDomainOptions: string[];
  existingCatchAlls: string[];
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
})));

/**
 * Returns the next to be filled in for name's help section.
 * 
 * If you're able to make a catch-all alias a second line will appear with information.
 */
const nameHelp = computed(() => {
  if (customDomainSelected.value && !props.existingCatchAlls.includes(`@${selectedDomain.value}`)) {
    return `${t('views.mail.sections.emailSettings.nameHelp')}\n\n${t('views.mail.sections.emailSettings.nameCatchAllHelp')}`
  }
  return t('views.mail.sections.emailSettings.nameHelp');
});

const validateEmailAlias = (value: string): string | null => {
  const isSharedDomain = allowedDomains.includes(selectedDomain.value);
  const isUsedCatchAll = props.existingCatchAlls.includes(`@${selectedDomain.value}`);

  // If we're a shared domain or a domain that already has a catch all we'll want to error out on min length.
  if ((isUsedCatchAll || isSharedDomain) && (!value || value.length < 3)) {
    return t('views.mail.sections.emailSettings.nameValidationErrorMinLength');
  }

  // Catch-all domain for #446
  if (!isUsedCatchAll && (!value || value === '*')) {
    return null;
  }

  if (value.length > 40) {
    return t('views.mail.sections.emailSettings.nameValidationErrorMaxLength');
  }

  const validPattern = /^[a-z0-9_]+$/;
  if (!validPattern.test(value)) {
    return t('views.mail.sections.emailSettings.nameValidationErrorPattern');
  }

  return null;
};

const onEmailAliasInput = () => {
  validationError.value = validateEmailAlias(emailAlias.value);
};

const onSubmit = () => {
  validationError.value = validateEmailAlias(emailAlias.value);

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
  validationError.value = validateEmailAlias(emailAlias.value);
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
</style>
