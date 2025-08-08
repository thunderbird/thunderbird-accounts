<script setup>
import MessageBar from '@/vue/components/MessageBar.vue';

const actionUrl = window._page.currentView?.actionUrl;
const actionText = window._page.currentView?.actionText;
</script>

<script>
export default {
  name: 'ErrorView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('errorTitle') }}</h2>
    <message-bar/>
    <template v-if="actionUrl">
      <a :href="actionUrl" data-testid="action-url">{{ actionText }}</a>
    </template>
  </div>
</template>

<style scoped>
</style>
