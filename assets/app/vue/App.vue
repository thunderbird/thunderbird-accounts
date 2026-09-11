<script setup lang="ts">
import HeaderBar from '@/components/HeaderBar.vue';
import TrafficBanner from '@/components/TrafficBanner.vue';
import FooterBar from '@/components/FooterBar.vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { SERVER_MESSAGE_LEVEL } from '@/types';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { onMounted, ref } from 'vue';
import { isStorageBlocked } from '@/utils';

const { t } = useI18n();
const serverMessages = ref(window._page?.serverMessages ?? []);

// When the browser blocks cookies/storage the user cannot authenticate, so
// tell them to enable cookies instead of leaving the app quietly broken.
// Checked once at setup; no reactivity needed.
const cookiesBlocked = isStorageBlocked();
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

const route = useRoute();
const router = useRouter();

let isInitialNavigation = true;

router.afterEach(() => {
  if (isInitialNavigation) {
    isInitialNavigation = false;
    return;
  }

  serverMessages.value = [];
});

onMounted(() => {
  window.document.body.dataset['testid'] = 'vue-app';
});
</script>

<template>
  <!-- Rendered outside the app-template branch so a cookie-blocked user sees it
       everywhere, including unauthenticated routes (sign-up, error, 404) that
       use the bare router-view below. -->
  <section class="server-messages cookies-blocked" v-if="cookiesBlocked">
    <notice-bar
      class="server-message"
      data-testid="cookies-disabled-notice"
      :type="NoticeBarTypes.Critical"
    >
      {{ t('cookiesDisabled.message') }}
    </notice-bar>
  </section>

  <div class="page-container" v-if="route?.meta?.useAppTemplate ?? true">
    <traffic-banner />
    <header-bar />

    <section class="server-messages" v-if="serverMessages.length">
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

    <main>
      <router-view />
    </main>

    <footer-bar />
  </div>
  <router-view v-else />
</template>

<style scoped>
.page-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--colour-neutral-lower);
}

main {
  flex: 1 1 auto;
  padding: 3rem 1rem;
  width: 100%;
  max-width: 1280px;
}

.server-messages {
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  .server-message {
    max-width: 60rem;
    margin: 1rem;
  }
}

@media (min-width: 1024px) {
  main {
    margin: 0 auto;
    padding: 3rem 3.5rem;
  }
}
</style>
