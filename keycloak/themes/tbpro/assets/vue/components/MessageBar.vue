<script setup>
import { NoticeBar, NoticeBarTypes } from "@thunderbirdops/services-ui";
import { computed } from "vue";

const message = window._page?.message;
const supportUrl = window._page?.supportUrl || window._page?.currentView?.supportUrl;

const messageType = computed(() => {
  // Make sure it's within the available types for noticebar
  if (Object.values(NoticeBarTypes).indexOf(message?.type) !== -1) {
    return message.type;
  }
  return 'info';
});

const formattedSummary = computed(() => {
  if (!message?.summary) return '';
  if (supportUrl && message.summary.includes('contact support')) {
    return message.summary.replace(
      'contact support',
      `<a href="${supportUrl}" class="support-link">contact support</a>`
    );
  }
  return message.summary;
});
</script>

<template>
  <notice-bar data-testid="notice-bar" class="notice-bar" :type="messageType" v-if="message?.type">
    <span v-html="formattedSummary"></span>
  </notice-bar>
</template>

<style scoped>
.notice-bar {
  margin-block-end: 1.5rem;
}

:deep(.support-link) {
  color: inherit;
  text-decoration: underline;
}
</style>
