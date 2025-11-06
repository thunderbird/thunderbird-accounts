<script setup lang="ts">
import HeaderBar from '@/components/HeaderBar.vue';
import FooterBar from '@/components/FooterBar.vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { SERVER_MESSAGE_LEVEL } from '@/types';

const serverMessages = window._page?.serverMessages ?? [];
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

<template>
  <div class="page-container">
    <header-bar />

    <section class="server-messages" v-if="serverMessages">
      <notice-bar
        class="server-message"
        v-for="message in serverMessages"
        :key="message.message"
        :type="serverLevelToNoticeBarType(message.level)"
      >
        {{ message.message }}
      </notice-bar>
    </section>

    <main>
      <router-view />
    </main>

    <footer-bar />
  </div>
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
  justify-content: center;
  gap: 1rem;

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
