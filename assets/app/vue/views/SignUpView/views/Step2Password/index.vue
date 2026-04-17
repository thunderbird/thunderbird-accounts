<script setup lang="ts">
import { useI18n } from 'vue-i18n';

import { TextInput } from '@thunderbirdops/services-ui';
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';
import SignUpLayout from '../../components/SignUpLayout.vue';

const { t } = useI18n();
const loading = ref(false);

const signUpFlowStore = useSignUpFlowStore();

const { fullUsername, password, confirmPassword, name } = storeToRefs(signUpFlowStore);
const { nextStep } = signUpFlowStore;
const confirmPasswordError = ref(null);

const onSubmit = async () => {
  loading.value = true;
  confirmPasswordError.value = null;

  if (password.value !== confirmPassword.value) {
    confirmPasswordError.value = t('views.mail.views.signUp.step2.confirmPasswordDoesNotMatchError');
    loading.value = false;
    return;
  }

  nextStep();
};
</script>

<script lang="ts">
export default {
  name: 'Step2Password'
};
</script>

<template>
  <sign-up-layout step-id="step-password" :title="$t('views.mail.views.signUp.step2.title')"
    :subtitle="$t('views.mail.views.signUp.step2.subtitle')" :submitDisabled="loading"
    :submitTitle="$t('views.mail.views.signUp.continue')" @submit="onSubmit">
    <template v-slot:notice-bars>
      <slot name="notice-bars" />
    </template>
    <template v-slot:form-elements>
      <!-- Send some hints to any password managers out there that this is something to save -->
      <input type="text" name="username" autocomplete="username" v-model="fullUsername" hidden>

      <text-input minlength="12" data-testid="password-input" name="password" type="password" required
        autocomplete="new-password" :help="$t('views.mail.views.signUp.step2.passwordHelp')" v-model="password">
        {{ $t('views.mail.views.signUp.fields.password') }}
      </text-input>

      <text-input minlength="12" data-testid="confirm-password-input" name="confirmPassword" type="password"
        required autocomplete="new-password" :error="confirmPasswordError"
        :help="$t('views.mail.views.signUp.step2.confirmPasswordHelp')" v-model="confirmPassword">
        {{ $t('views.mail.views.signUp.fields.confirmPassword') }}
      </text-input>

      <text-input data-testid="name-input" name="name" autocomplete="name"
        :help="$t('views.mail.views.signUp.step2.yourNameHelp')" v-model="name">
        {{ $t('views.mail.views.signUp.fields.yourName') }}
      </text-input>

      <slot name="form-extras" />
    </template>
  </sign-up-layout>
</template>
