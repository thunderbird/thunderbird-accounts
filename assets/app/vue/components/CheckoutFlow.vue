<script setup>
import {ref, onMounted} from 'vue';
import {initializePaddle} from '@paddle/paddle-js';

const isLoading = ref(true);
const priceItems = ref({});
const isPaddleNotConfiguredCorrectly = ref(false);
const didReceivePaddleError = ref(false);
const errorTitle = ref('');

const paddleToken = window._page.paddleToken;
const paddleEnvironment = window._page.paddleEnvironment;
const paddlePlanInfo = window._page.paddlePlanInfo;
const successRedirect = window._page.successRedirect;
const signedUserId = window._page.signedUserId;

const baseUrl = window.location.toString().replace(window.location.pathname, '');
const successUrl = `${baseUrl}${successRedirect}`;

let Paddle; // The initialized Paddle instance.

const paddleItems = paddlePlanInfo.map((priceId) => ({
  quantity: 1,
  priceId,
}));

onMounted(() => {
  if (!paddleToken || paddleItems.length === 0) {
    isPaddleNotConfiguredCorrectly.value = true;
    errorTitle.value = 'Configuration Error';
    isLoading.value = false;
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
    customData: {
      signed_user_id: signedUserId,
    },
  });
}

async function initPaddle(items, fn) {
  let result = null;
  try {
    result = await Promise.resolve(Paddle.PricePreview({items}));
  } catch (error) {
    didReceivePaddleError.value = true;
    errorTitle.value = 'Server Error';
    console.error(error);
    isLoading.value = false;
    return;
  }

  const {lineItems} = result.data.details;
  lineItems.forEach((item) => {
    const productName = item.product.name;
    const {total} = item.formattedTotals;
    const {name, description, id} = item.price;
    if (!priceItems.value.hasOwnProperty(productName)) {
      priceItems.value[productName] = [];
    }
    priceItems.value[productName].push({
      total,
      name,
      description,
      id,
    });
  });

  isLoading.value = false;
}
</script>
<template>
  <div class="pricing-page-container">
    <h1>Choose your plan</h1>
    <div v-if="isPaddleNotConfiguredCorrectly || didReceivePaddleError" class="paddle-error" data-testid="pricing-error">
      <h3>{{ errorTitle }}</h3>
      <p>Cannot complete checkout at this time.</p>
    </div>
    <div v-else-if="isLoading" class="loader-outside" data-testid="pricing-loader">
      <div class="loader-inside"></div>
    </div>
    <div v-else-if="Object.values(priceItems).length > 0" class="pricing-grid" data-testid="pricing-grid">
      <div v-for="(prices, productName) in priceItems" data-testid="pricing-grid-plan-item">
        <h2>{{ productName }}</h2>
        <div v-for="item in prices" data-testid="pricing-grid-price-item">
          <h3>{{ item.name }}</h3>
          <p>{{ item.total }}</p>
          <button @click="openCheckout(item.id)" data-testid="checkout-button">Select {{ item.total }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.pricing-grid {
  display: flex;
  gap: 2rem;
}
</style>