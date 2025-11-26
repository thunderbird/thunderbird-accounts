<script setup lang="ts">
// Import Keycloak theme's style
import '@kc/css/main.css';
import kcEn from '@/locales/en.kc.json';

// Import the BaseTemplate and RegisterView from Keycloak
import RegisterView from '@kc/vue/views/RegisterView/index.vue';
import BaseTemplate from '@kc/vue/BaseTemplate.vue';

// Import our i18n composable
import i18nInstance from '@/composables/i18n';
import CsrfToken from '@/components/forms/CsrfToken.vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { SERVER_MESSAGE_LEVEL } from '@/types';

// Note: We only support english right now
const locale = 'en';

// Keycloak also uses window page variables, so set them up as it expects
window._page.currentView = {
  errors: [],
  formAction: '/users/sign-up/',
  clientUrl: window.location.origin,
  currentLocale: locale,
};
window._page.pageId = 'sign-up';

// Merge some localization
i18nInstance.global.mergeLocaleMessage(locale, { ...(kcEn ?? {}) });

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
    <register-view>
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
    </register-view>
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
</style>
