<script setup>
import { NoticeBar, NoticeBarTypes } from "@thunderbirdops/services-ui";
import { computed } from "vue";

const message = window._page?.message;
const messageType = computed(() => {
  // Make sure it's within the available types for noticebar
  if (Object.values(NoticeBarTypes).indexOf(message.type) !== -1) {
    return message.type;
  }
  return 'info';
});
</script>

<template>
  <notice-bar class="notice-bar" :type="messageType" v-if="message?.type">{{ message?.summary }}</notice-bar>
</template>

<style scoped>
.notice-bar {
  margin-bottom: var(--space-12);
}
</style>
