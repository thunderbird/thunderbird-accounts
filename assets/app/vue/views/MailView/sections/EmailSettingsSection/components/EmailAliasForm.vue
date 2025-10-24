<script setup lang="ts">
import { ref, computed, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { TextInput, SelectInput, PrimaryButton } from '@thunderbirdops/services-ui';

// Types
import { EMAIL_ALIAS_STEP } from '../types';

const { t } = useI18n();

const props = defineProps<{
  allowedDomains: string[];
}>();

const emit = defineEmits<{
  'add-alias': [emailAlias: string, domain: string];
}>();

const step = ref<EMAIL_ALIAS_STEP>(EMAIL_ALIAS_STEP.INITIAL);
const emailAlias = ref(null);
const selectedDomain = ref(null);
const formRef = useTemplateRef('formRef');

const allowedDomainsOptions = computed(() => props.allowedDomains.map((domain) => ({
  label: domain,
  value: domain,
})));

const onSubmit = () => {
  if (formRef.value.checkValidity()) {
    emit('add-alias', emailAlias.value, selectedDomain.value);
    emailAlias.value = null;
    selectedDomain.value = null;
    step.value = EMAIL_ALIAS_STEP.INITIAL;
  }
};
</script>

<template>
  <template v-if="step === EMAIL_ALIAS_STEP.INITIAL">
    <primary-button variant="outline" @click="step = EMAIL_ALIAS_STEP.SUBMIT">
      {{ t('views.mail.sections.emailSettings.addEmailAlias') }}
    </primary-button>
  </template>

  <template v-else-if="step === EMAIL_ALIAS_STEP.SUBMIT">
    <form @submit.prevent="onSubmit" ref="formRef">
      <div class="email-alias-input-wrapper">
        <text-input name="email-alias" v-model="emailAlias" :help="t('views.mail.sections.emailSettings.nameHelp')" required>
          {{ t('views.mail.sections.emailSettings.name') }}
        </text-input>
        <span>@</span>
        <select-input name="domain" :options="allowedDomainsOptions" v-model="selectedDomain" required>
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