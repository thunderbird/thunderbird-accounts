<script setup lang="ts">
import { useI18n } from 'vue-i18n';

import { TextInput, BrandButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { computed, ref, useTemplateRef } from 'vue';
import { useRoute } from 'vue-router';
import { PhArrowRight } from '@phosphor-icons/vue';
import MessageBar from '@kc/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@kc/svg/thunderbird-pro-light.svg';
import { useDebounceFn } from '@vueuse/core';
import { isUsernameAvailable } from './api';
import { storeToRefs } from 'pinia';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';

const route = useRoute();
const { t } = useI18n();

const errors = window._page.currentView?.errors;
const formAction = window._page.currentView?.formAction;
const clientUrl = window._page.currentView?.clientUrl;
const tbProPrimaryDomain = `@${window._page.currentView?.tbProPrimaryDomain}`;
const attributeValues = window._page.currentView?.attributes;

const signUpFlowStore = useSignUpFlowStore();

const { username } = storeToRefs(signUpFlowStore);
const usernameOk = ref(false);
const usernameError = ref(null);

const usernameCheckDebounced = useDebounceFn(async () => {
  const response = await isUsernameAvailable(username.value);
  if (response === true) {
    usernameOk.value = true;
    usernameError.value = null;
    return;
  } 

  usernameOk.value = false;

  if (response === false) {
    usernameError.value = t('views.mail.views.signUp.step1.unknownError');
    return;
  }

  usernameError.value = response;
}, 500);

const onSubmit = async () => {
  await usernameCheckDebounced();
  if (!usernameOk) {
    return;
  }


};
</script>

<script lang="ts">
export default {
  name: 'Step1Username'
};
</script>

<template>
  <h2 data-testid="title">{{ $t('views.mail.views.signUp.step1.title') }}</h2>

  <slot name="notice-bars">
    <message-bar />
  </slot>

  <form @submit.prevent="onSubmit" @keyup.enter="onSubmit">
    <div class="form-elements">
      <text-input 
      data-testid="username-input" 
      id="partialUsername" 
      name="partialUsername" 
      required
      autocomplete="username" 
      @input="usernameCheckDebounced" 
      :error="usernameError" 
      :outerSuffix="tbProPrimaryDomain"
      :help="$t('views.mail.views.signUp.step1.usernameHelp', { 'domain': tbProPrimaryDomain })" 
      v-model="username">
        {{ $t('views.mail.views.signUp.fields.username') }}
      </text-input>
      <slot name="form-extras" />
    </div>
    <div class="buttons">
      <brand-button data-testid="submit-button" class="submit" @click="onSubmit">
        {{ $t('views.mail.views.signUp.next') }}

        <template #iconRight>
          <ph-arrow-right size="20" />
        </template>
      </brand-button>
    </div>
  </form>
</template>

<style scoped>
#i18n-workaround {
  display: none;
}

.hidden {
  display: none;
}

.notice-bar {
  position: absolute;
  top: 1rem;
  left: 1.5rem;
  right: 1.5rem;
  z-index: 1;
}

.logo-link {
  display: block;
  text-decoration: none;
  margin-block-end: 2.8125rem;

  .logo {
    height: 36px;
    width: auto;
    transition: opacity 0.2s ease;

    &:hover {
      opacity: 0.8;
    }
  }
}

h2 {
  font-size: 2.25rem;
  font-family: metropolis;
  font-weight: normal;
  letter-spacing: -0.36px;
  line-height: 1.2;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;

  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>
