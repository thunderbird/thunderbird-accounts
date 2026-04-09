<script setup lang="ts">
// Import Keycloak theme's style
import '@kc/css/main.css';
import kcEn from '@/locales/en.kc.json';

// Import the BaseTemplate and RegisterView from Keycloak
import RegisterView from '@kc/vue/views/RegisterView/index.vue';
import BaseTemplate from '@kc/vue/BaseTemplate.vue';

import Step1Username from './views/Step1Username/index.vue';

// Import our i18n composable
import i18nInstance from '@/composables/i18n';
import CsrfToken from '@/components/forms/CsrfToken.vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { SERVER_MESSAGE_LEVEL } from '@/types';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import ThunderbirdLogoLight from '@kc/svg/thunderbird-pro-light.svg';
import { useSignUpFlowStore } from './stores/signUpFlowStore';
import { storeToRefs } from 'pinia';

const { t } = useI18n();
const route = useRoute();
const signUpFlowStore = useSignUpFlowStore();
const isSignUpComplete = route.name === 'sign-up-complete';

const { lang, timezone } = storeToRefs(signUpFlowStore);

// We only support english right now :(
lang.value = 'en';
timezone.value = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';

// TODO: Remove me
// Keycloak also uses window page variables, so set them up as it expects
window._page.currentView = {
  errors: [],
  formAction: '/users/sign-up/',
  clientUrl: window.location.origin,
  currentLocale: lang.value,
  tbProPrimaryDomain: window._page.tbProPrimaryDomain,
  attributes: {
    'username': window._page?.formData?.username || '',
    'email': window._page?.formData?.email || '',
  }
};
window._page.pageId = route.name.toString();

// Load in our django error messages
const serverMessages = window._page.serverMessages;
const serverLevelToNoticeBarType = (level: SERVER_MESSAGE_LEVEL) => {
  switch (level) {
    case SERVER_MESSAGE_LEVEL.ERROR:
      return NoticeBarTypes.Critical;
    case SERVER_MESSAGE_LEVEL.SUCCESS:
      return NoticeBarTypes.Success;
    case SERVER_MESSAGE_LEVEL.WARNING:
      return NoticeBarTypes.Warning;
    default:
      return NoticeBarTypes.Info;
  }
};
</script>

<script lang="ts">
export default {
  name: 'SignUp',
};
</script>

<template>
  <base-template>
    <step1-username v-if="!isSignUpComplete">
      <template v-slot:notice-bars>
        <section class="server-messages" v-if="serverMessages !== null">
          <template v-for="message in serverMessages" :key="message.message">
            <notice-bar
              class="server-message"
              v-if="message.message.trim() !== ''"
              :type="serverLevelToNoticeBarType(message.level)"
            >
              {{ message.message }}
            </notice-bar>
          </template>
        </section>
      </template>
      <template v-slot:form-extras>
        <csrf-token />
      </template>
    </step1-username>
    <section v-else>
      <a href="/" class="logo-link">
        <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
      </a>
      <h2>{{ t('verifyTitle') }}</h2>
      <p>{{ t('emailVerifyInstruction') }}</p>
    </section>
  </base-template>
</template>

<style scoped>
.server-messages {
  width: 100%;
  display: flex;
  flex-direction: column;

  .server-message {
    max-width: 60rem;
    margin: 1rem 1rem 1rem 0;
  }
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

</style>
