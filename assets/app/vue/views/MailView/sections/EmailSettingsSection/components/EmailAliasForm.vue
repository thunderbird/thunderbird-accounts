<script setup lang="ts">
import { ref, computed, useTemplateRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { TextInput, SelectInput, PrimaryButton } from '@thunderbirdops/services-ui';

// Types
import { EMAIL_ALIAS_STEP } from '../types';

const { t } = useI18n();

const props = defineProps<{
  allDomainOptions: string[];
}>();

const emit = defineEmits<{
  'add-alias': [emailAlias: string, domain: string];
}>();

// And the domains in the settings.ALLOWED_EMAIL_DOMAINS from the backend
const allowedDomains = window._page.allowedDomains || [];

const step = ref<EMAIL_ALIAS_STEP>(EMAIL_ALIAS_STEP.INITIAL);
const emailAlias = ref(null);
const selectedDomain = ref(props.allDomainOptions[0] ?? null);
const formRef = useTemplateRef('formRef');
const validationError = ref<string | null>(null);

const allDomainOptions = computed(() => props.allDomainOptions.map((domain) => ({
  label: domain,
  value: domain,
})));

const validateEmailAlias = (value: string): string | null => {
  if (!value) {
    return null; // Let built-in required validation handle empty values
  }

  // This rule should only apply to allowed domains, not custom domains
  if (allowedDomains.includes(selectedDomain.value) && value.length < 3) {
    return t('views.mail.sections.emailSettings.nameValidationErrorMinLength');
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
    emailAlias.value = null;
    selectedDomain.value = props.allDomainOptions[0] ?? null;
    validationError.value = null;
    step.value = EMAIL_ALIAS_STEP.INITIAL;
  }
};

// Validate on selected domain change as well
watch(selectedDomain, () => {
  validationError.value = validateEmailAlias(emailAlias.value);
})
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
          :help="t('views.mail.sections.emailSettings.nameHelp')"
          :error="validationError"
          required
        >
          {{ t('views.mail.sections.emailSettings.name') }}
        </text-input>
        <span>@</span>
        <select-input name="domain" :options="allDomainOptions" v-model="selectedDomain" required>
          {{ t('views.mail.sections.emailSettings.domain') }}
        </select-input>
      </div>

      <primary-button @click="onSubmit">
        {{ t('views.mail.sections.emailSettings.submit') }}
      </primary-button>
    </form>
  </template>
</template>

<style scoped>
:deep(.tooltip) {
  min-width: 200px;
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
</style>