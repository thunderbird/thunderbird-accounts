<script setup>
import MessageBar from '@/vue/components/MessageBar.vue';

const restartFlowUrl = window._page.currentView?.restartFlowUrl;
const loginUrl = window._page.currentView?.loginUrl;
</script>

<script>
export default {
  name: 'PageExpiredView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('pageExpiredTitle') }}</h2>
    <message-bar/>
    <div class="buttons">
      <p>{{ $t('pageExpiredMsg1') }} <a data-testid="restart-flow-url" :href="restartFlowUrl">{{ $t('doClickHere') }}</a></p>
      <p>{{ $t('pageExpiredMsg2') }} <a data-testid="login-url" :href="loginUrl">{{ $t('doClickHere') }}</a></p>
    </div>
  </div>
</template>

<style scoped>
.buttons {
  margin-top: var(--space-24);
  width: 100%;
}
</style>
