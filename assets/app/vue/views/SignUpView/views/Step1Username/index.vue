<script setup lang="ts">
import { useI18n } from 'vue-i18n';

import { TextInput } from '@thunderbirdops/services-ui';
import { onMounted, ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { isUsernameAvailable } from './api';
import { storeToRefs } from 'pinia';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';
import SignUpLayout from '../../components/SignUpLayout.vue';

const USERNAME_MIN_LENGTH = 3;
const USERNAME_MAX_LENGTH = 150;

const { t } = useI18n();
const tbProPrimaryDomain = `@${window._page.currentView?.tbProPrimaryDomain}`;
const loading = ref(false);

const signUpFlowStore = useSignUpFlowStore();

const { username } = storeToRefs(signUpFlowStore);
const { nextStep } = signUpFlowStore;
const usernameOk = ref(false);
const usernameError = ref(null);

const usernameCheckDebounced = useDebounceFn(async () => {
  loading.value = false;

  const value = username.value ?? '';

  if (value.length < USERNAME_MIN_LENGTH) {
    usernameOk.value = false;
    usernameError.value = t('views.mail.views.signUp.step1.usernameTooShort', {
      minLength: USERNAME_MIN_LENGTH
    });
    return;
  }

  if (value.length > USERNAME_MAX_LENGTH) {
    usernameOk.value = false;
    usernameError.value = t('views.mail.views.signUp.step1.usernameTooLong', {
      maxLength: USERNAME_MAX_LENGTH
    });
    return;
  }

  const { success, error } = await isUsernameAvailable(value);

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

  // Validate any pre-filled username (from query param or session storage) since
  // programmatic assignment doesn't set the input's dirty flag and therefore
  // skips the browser's built-in minlength/maxlength constraint checks.
  if (username.value) {
    loading.value = true;
    usernameCheckDebounced();
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
    @submit="onSubmit">
    <template v-slot:notice-bars>
      <slot name="notice-bars"/>
    </template>
    <template v-slot:form-elements>
      <text-input 
      data-testid="username-input" 
      name="partialUsername" 
      required
      minlength="3"
      maxlength="150"
      autocomplete="username" 
      @input="usernameCheckDebounced"
      :error="usernameError"
      :outerSuffix="tbProPrimaryDomain"
      :placeholder="$t('views.mail.views.signUp.step1.usernamePlaceholder')"
      :help="$t('views.mail.views.signUp.step1.usernameHelp', { 'domain': tbProPrimaryDomain })"
      v-model="username">
        {{ $t('views.mail.views.signUp.fields.username') }}
      </text-input>
      <slot name="form-extras" />
    </template>
  </sign-up-layout>
</template>
