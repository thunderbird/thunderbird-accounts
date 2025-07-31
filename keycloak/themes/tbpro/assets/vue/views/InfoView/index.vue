<script setup>
import { NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

// For some reason message here is not set in the template only the view...
const messageHeader = ref(window._page.currentView?.messageHeader);
const message = ref(window._page.message);
const actionUrl = ref(window._page.currentView?.actionUrl);
const actionText = ref(window._page.currentView?.actionText);
const requiredActions = ref(window._page.currentView?.requiredActions);
console.log(requiredActions.value);
</script>

<script>
export default {
  name: 'InfoView'
}
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
.panel {
  margin: 30px
}

.notice-bar {
  margin-bottom: var(--space-12);
}
</style>