<script setup>
const restartFlowUrl = window._page.currentView?.restartFlowUrl;
const loginUrl = window._page.currentView?.loginUrl;
</script>

<script>
export default {
  name: 'PageExpiredView'
};
</script>

<template>
  <h2>{{ $t('pageExpiredTitle') }}</h2>
  <div class="buttons">
    <p>{{ $t('pageExpiredMsg1') }} <a data-testid="restart-flow-url" :href="restartFlowUrl">{{ $t('doClickHere') }}</a></p>
    <p>{{ $t('pageExpiredMsg2') }} <a data-testid="login-url" :href="loginUrl">{{ $t('doClickHere') }}</a></p>
  </div>
</template>

<style scoped>
.buttons {
  margin-top: var(--space-24);
  width: 100%;
}
</style>
