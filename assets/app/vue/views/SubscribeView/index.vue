<script setup lang="ts">
import CheckoutStep from '@/views/SubscribeView/components/CheckoutStep.vue';
import PaymentPendingStep from '@/views/SubscribeView/components/PaymentPendingStep.vue';

const isAwaitingPaymentVerification = window._page?.isAwaitingPaymentVerification;
</script>

<script lang="ts">
export default {
  name: 'SubscribeView',
};
</script>

<template>
  <div class="subscribe-view">
    <payment-pending-step v-if="isAwaitingPaymentVerification" />
    <checkout-step v-else />
  </div>
</template>

<style scoped>
.subscribe-view {
  width: 100%;
}
</style>
