<script setup lang="ts">
import { TextInput } from '@thunderbirdops/services-ui';
import { onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';
import SignUpLayout from '../../components/SignUpLayout.vue';

const loading = ref(false);

const signUpFlowStore = useSignUpFlowStore();

const { verificationEmail } = storeToRefs(signUpFlowStore);
const { submit } = signUpFlowStore;
const emailError = ref(null);

const onSubmit = async () => {
  loading.value = true;
  const response = await submit();

  if (response === true) {
    window.location.href = '/sign-up/complete';
  } else {
    window.setTimeout(() => {
      loading.value = false;
    }, 0);
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
      <text-input data-testid="verification-email-input" name="verification-email" required autocomplete="email"
        :error="emailError" :help="$t('views.mail.views.signUp.step3.verificationEmailHelp')"
        :placeholder="$t('views.mail.views.signUp.step3.verificationEmailPlaceholder')" v-model="verificationEmail">
        {{ $t('views.mail.views.signUp.fields.verificationEmail') }}
      </text-input>
      <slot name="form-extras" />
    </template>
  </sign-up-layout>
</template>
