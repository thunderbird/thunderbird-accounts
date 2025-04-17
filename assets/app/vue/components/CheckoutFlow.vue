<script setup>
import { ref, onMounted } from 'vue';
import { initializePaddle } from '@paddle/paddle-js';

const isLoading = ref(true);
const priceItems = ref([]);
const isPaddleTokenMissing = ref(false);
const didReceivePaddleError = ref(false);
const errorTitle = ref('');

const paddleToken = window._page.paddleToken;
const paddleEnvironment = window._page.paddleEnvironment;
const paddlePriceIdLo = window._page.paddlePriceIdLo;
const paddlePriceIdMd = window._page.paddlePriceIdMd;
const paddlePriceIdHi = window._page.paddlePriceIdHi;
const successRedirect = window._page.successRedirect;

const baseUrl = window.location
  .toString()
  .replace(window.location.pathname, '');
const successUrl = `${baseUrl}${successRedirect}`;

let Paddle; // The initialized Paddle instance.

const paddleItems = [paddlePriceIdLo, paddlePriceIdMd, paddlePriceIdHi].map(
  (priceId) => ({
    quantity: 1,
    priceId,
  })
);

onMounted(() => {
  if (!paddleToken) {
    isPaddleTokenMissing.value = true;
    errorTitle.value = 'Configuration Error';
    return;
  }

  initializePaddle({
    environment: paddleEnvironment,
    token: paddleToken,
  }).then((paddleInstance) => {
    if (!paddleInstance) {
      return;
    }
    Paddle = paddleInstance;
    initPaddle(paddleItems);
  });
});

function openCheckout(priceId) {
  Paddle.Checkout.open({
    settings: {
      successUrl,
    },
    items: [
      {
        quantity: 1,
        priceId,
      },
    ],
  });
}

function initPaddle(items, fn) {
  Paddle.PricePreview({ items })
    .then((result) => {
      const { lineItems } = result.data.details;
      priceItems.value = lineItems.map((item) => {
        const { total } = item.formattedTotals;
        const { name, description, id } = item.price;
        return {
          total,
          name,
          description,
          id,
        };
      });
      isLoading.value = false;
    })
    .then(fn)
    .catch((error) => {
      didReceivePaddleError.value = true;
      errorTitle.value = 'Server Error';
      console.error(error);
    })
    .finally(() => (isLoading.value = false));
}
</script>
<template>
  <div class="pricing-page-container">
    <h1>Choose your plan</h1>
    <div
      v-if="isPaddleTokenMissing || didReceivePaddleError"
      class="paddle-error"
    >
      <h3>{{ errorTitle }}</h3>
      <p>Cannot complete checkout at this time.</p>
    </div>
    <div v-else-if="isLoading" class="loader-outside">
      <div class="loader-inside"></div>
    </div>
    <div v-else class="pricing-grid" id="pricing-grid">
      <div v-for="item in priceItems">
        <h3>{{ item.name }}</h3>
        <p>{{ item.description }}</p>
        <p>{{ item.total }}</p>
        <button @click="openCheckout(item.id)">Select {{ item.total }}</button>
      </div>
    </div>
  </div>
</template>
