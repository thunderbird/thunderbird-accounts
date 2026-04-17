<script setup lang="ts">
import { useI18n } from 'vue-i18n';

import { TextInput } from '@thunderbirdops/services-ui';
import { onMounted, ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { isUsernameAvailable } from './api';
import { storeToRefs } from 'pinia';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';
import SignUpLayout from '../../components/SignUpLayout.vue';

const { t } = useI18n();
const tbProPrimaryDomain = `@${window._page.currentView?.tbProPrimaryDomain}`;
const loading = ref(false);

const signUpFlowStore = useSignUpFlowStore();

const { username } = storeToRefs(signUpFlowStore);
const { nextStep } = signUpFlowStore;
const usernameOk = ref(false);
const usernameError = ref(null);

const usernameCheckDebounced = useDebounceFn(async () => {
  const { success, error } = await isUsernameAvailable(username.value);
  loading.value = false;

  if (success === true) {
    usernameOk.value = true;
    usernameError.value = null;
    return;
  }

  usernameOk.value = false;
  if (error === false) {
    usernameError.value = t('views.mail.views.signUp.step1.unknownError');
    return;
  }

  usernameError.value = error;
}, 250);

const onSubmit = async () => {
  loading.value = true;

  await usernameCheckDebounced();
  if (!usernameOk.value) {
    return;
  }

  nextStep();
};


onMounted(() => {
  // Prefer a query param username over one that might be in storage.
  if (window._page.currentView?.attributes?.username) {
    username.value = window._page.currentView?.attributes?.username;
  }
});

</script>

<script lang="ts">
export default {
  name: 'Step1Username'
};
</script>

<template>
  <sign-up-layout step-id="step-username" :title="$t('views.mail.views.signUp.step1.title')"
    :subtitle="$t('views.mail.views.signUp.step1.subtitle')" :submitDisabled="loading || !!usernameError"
    :submitTitle="$t('views.mail.views.signUp.continue')" @submit="onSubmit">
    <template v-slot:notice-bars>
      <slot name="notice-bars"/>
    </template>
    <template v-slot:form-elements>
      <text-input 
      data-testid="username-input" 
      id="partialUsername" 
      name="partialUsername" 
      required
      maxlength="150"
      autocomplete="username" 
      @input="usernameCheckDebounced"
      :error="usernameError"
      :outerSuffix="tbProPrimaryDomain"
      :help="$t('views.mail.views.signUp.step1.usernameHelp', { 'domain': tbProPrimaryDomain })"
      v-model="username">
        {{ $t('views.mail.views.signUp.fields.username') }}
      </text-input>
      <slot name="form-extras" />
    </template>
  </sign-up-layout>
</template>
