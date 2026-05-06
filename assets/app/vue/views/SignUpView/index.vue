<script setup lang="ts">
// Import Keycloak theme's style
import '@kc/css/main.css';

// Import the BaseTemplate and RegisterView from Keycloak
import BaseTemplate from '@kc/vue/BaseTemplate.vue';

import Step1Username from './views/Step1Username/index.vue';
import Step2Password from './views/Step2Password/index.vue';
import Step3Verify from './views/Step3Verify/index.vue';
import SignUpLayout from './components/SignUpLayout.vue';

// Import our i18n composable
import CsrfToken from '@/components/forms/CsrfToken.vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { SignUpSteps, useSignUpFlowStore } from './stores/signUpFlowStore';
import { storeToRefs } from 'pinia';
import { PhX } from '@phosphor-icons/vue';

const { t } = useI18n();
const route = useRoute();
const signUpFlowStore = useSignUpFlowStore();
const isSignUpComplete = route.name === 'sign-up-complete';

const { lang, timezone, step, errorMessage } = storeToRefs(signUpFlowStore);

// We only support english right now :(
lang.value = 'en';
timezone.value = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';

// TODO: Remove me
// Keycloak also uses window page variables, so set them up as it expects
window._page.currentView = {
  errors: [],
  clientUrl: window.location.origin,
  currentLocale: lang.value,
  tbProPrimaryDomain: window._page.tbProPrimaryDomain,
  attributes: {
    'username': route.query?.username || null,
    'email': route.query?.email || null,
  }
};
window._page.pageId = route.name.toString();

// Map of enum steps and SFC
const stepSFCMap = {
  [SignUpSteps.USERNAME]: Step1Username,
  [SignUpSteps.PASSWORD]: Step2Password,
  [SignUpSteps.VERIFY]: Step3Verify,
}
</script>

<script lang="ts">
export default {
  name: 'SignUp',
};
</script>

<template>
  <base-template>
    <component v-if="!isSignUpComplete" :is="stepSFCMap[step]">
      <template v-slot:notice-bars>
        <!-- Orca at least will only detect updated dom elements not "new" dom elements. 
        So we need a wrapper that updates, otherwise we won't announce anything -->
        <div aria-live="assertive">
          <notice-bar class="server-message" :type="NoticeBarTypes.Critical" v-if="errorMessage !== null">
            {{ errorMessage }}

            <template #cta>
              <button :title="t('views.error.dismiss')" class="close-button" @click="errorMessage = null">
                <ph-x size="16" />
              </button>
            </template>
          </notice-bar>
        </div>
      </template>
      <template v-slot:form-extras>
        <csrf-token />
      </template>
    </component>
    <section v-else>
      <sign-up-layout step-id="step-check-your-mail" :title="$t('views.mail.views.signUp.step4.title')"
        :subtitle="$t('views.mail.views.signUp.step4.subtitle')" :hide-actions="true" :submit-disabled="false">
        <template v-slot:notice-bars>
          <slot name="notice-bars" />
        </template>
      </sign-up-layout>
    </section>
  </base-template>
</template>

<style scoped>
.close-button {
  background-color: transparent;
  border: none;
  display: flex;
  align-items: center;

  :hover {
    cursor: pointer;
  }
}
</style>
