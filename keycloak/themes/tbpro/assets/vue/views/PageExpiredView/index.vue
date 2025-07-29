<script setup>
import { ref } from "vue";

const restartFlowUrl = ref(window._page.currentView?.restartFlowUrl);
const loginUrl = ref(window._page.currentView?.loginUrl);
</script>

<script>
export default {
  name: 'PageExpiredView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('pageExpiredTitle') }}</h2>
      <div class="buttons">
        <p>{{ $t('pageExpiredMsg1') }} <a :href="restartFlowUrl">{{ $t('doClickHere') }}</a></p>
        <p>{{ $t('pageExpiredMsg2') }} <a :href="loginUrl">{{ $t('doClickHere') }}</a></p>
      </div>
  </div>
</template>

<style scoped>
.panel {
  margin: 30px
}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.buttons {
  width: 100%;
  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>