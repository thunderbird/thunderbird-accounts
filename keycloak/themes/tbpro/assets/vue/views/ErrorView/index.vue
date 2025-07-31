<script setup>
import { NoticeBar } from "@thunderbirdops/services-ui";
import { ref } from "vue";

// For some reason message here is not set in the template only the view...
const message = ref(window._page.message);
const actionUrl = ref(window._page.currentView?.actionUrl);
const actionText = ref(window._page.currentView?.actionText);

</script>

<script>
export default {
  name: 'ErrorView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('errorTitle') }}</h2>
    <notice-bar :type="message.type" v-if="message.type">{{ message.summary }}</notice-bar>
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