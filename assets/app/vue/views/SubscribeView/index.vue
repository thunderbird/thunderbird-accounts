<script setup lang="ts">
import CheckoutStep from '@/views/SubscribeView/components/CheckoutStep.vue';
</script>

<script lang="ts">
export default {
  name: 'SubscribeView',
};
</script>

<template>
  <div class="subscribe-view">
    <checkout-step />
  </div>
</template>

<style scoped>
.subscribe-view {
  width: 100%;
}
</style>
