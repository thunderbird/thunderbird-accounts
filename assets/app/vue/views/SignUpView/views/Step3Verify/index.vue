<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDebounceFn } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { TextInput } from '@thunderbirdops/services-ui';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';
import SignUpLayout from '../../components/SignUpLayout.vue';
import { isRecoveryEmailInUse } from './api';

const { t } = useI18n();

const loading = ref(false);

const signUpFlowStore = useSignUpFlowStore();

const { verificationEmail } = storeToRefs(signUpFlowStore);
const { submit } = signUpFlowStore;
const emailOk = ref(false);
const emailError = ref(null);

const recoveryEmailCheckDebounced = useDebounceFn(async () => {
  const { success, error } = await isRecoveryEmailInUse(verificationEmail.value);
  loading.value = false;

  if (success === true) {
    emailOk.value = true;
    emailError.value = null;
    return;
  }

  emailOk.value = false;
  if (error === false) {
    emailError.value = t('views.mail.views.signUp.step3.unknownError');
    return;
  }

  emailError.value = error;
}, 250);

const onSubmit = async () => {
  loading.value = true;

  await recoveryEmailCheckDebounced();
  if (!emailOk.value) {
    return;
  }

  const response = await submit();

  if (response === true) {
    window.location.href = '/sign-up/complete';
  } else {
    await nextTick();
    loading.value = false;
  }
};

onMounted(() => {
  // Prefer a query param username over one that might be in storage.
  if (window._page.currentView?.attributes?.email) {
    verificationEmail.value = window._page.currentView?.attributes?.email;
  }
});
</script>

<script lang="ts">
export default {
  name: 'Step3Verify'
};
</script>

<template>
  <sign-up-layout step-id="step-verify-email" :title="$t('views.mail.views.signUp.step3.title')"
    :subtitle="$t('views.mail.views.signUp.step3.subtitle')" :submitDisabled="loading || !!emailError"
    @submit="onSubmit" :submit-title="$t('views.mail.views.signUp.step3.action')">
    <template v-slot:notice-bars>
      <slot name="notice-bars" />
    </template>
    <template v-slot:form-elements>
      <text-input
        data-testid="verification-email-input"
        name="verification-email"
        required
        autocomplete="email"
        @input="recoveryEmailCheckDebounced"
        :error="emailError"
        :help="$t('views.mail.views.signUp.step3.verificationEmailHelp')"
        :placeholder="$t('views.mail.views.signUp.step3.verificationEmailPlaceholder')"
        v-model="verificationEmail"
      >
        {{ $t('views.mail.views.signUp.fields.verificationEmail') }}
      </text-input>
      <slot name="form-extras" />
    </template>
  </sign-up-layout>
</template>
