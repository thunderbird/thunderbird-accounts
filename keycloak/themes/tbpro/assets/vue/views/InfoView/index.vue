<script setup>
import {NoticeBar} from "@thunderbirdops/services-ui";

const message = window._page.message;
const messageHeader = window._page.currentView?.messageHeader;
const actionUrl = window._page.currentView?.actionUrl;
const actionText = window._page.currentView?.actionText;
</script>

<script>
export default {
  name: 'InfoView'
};
</script>

<template>
  <div class="panel">
    <h2>
      <template v-if="messageHeader">
        {{ messageHeader }}
      </template>
      <template v-else>
        {{ message?.summary }}
      </template>
    </h2>
    <notice-bar :type="message.type" v-if="message?.type">{{ message.summary }}</notice-bar>
    <template v-if="actionUrl">
      <a :href="actionUrl">{{ actionText }}</a>
    </template>
  </div>
</template>

<style scoped>
</style>
