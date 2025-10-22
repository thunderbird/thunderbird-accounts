<script setup lang="ts">
import {useI18n} from 'vue-i18n';
import {VisualDivider} from '@thunderbirdops/services-ui';
import {initializePaddle} from "@paddle/paddle-js";
import CardContainer from "@/components/CardContainer.vue";
import {computed, ref} from "vue";

//const {t} = useI18n();

const csrfToken = window._page.csrfToken;

const initCurrencyFormatter = (code: string) => {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: code,
  });
}

let currency_formatter = initCurrencyFormatter('USD');

const order_summary = ref({
  currency_code: null,
  total: null,
  planName: null,
  planDuration: null,
  planDurationLong: null,
  quantity: null,
  subtotal: null,
  taxes: null,
  dueToday: null,
  dueOnRenewal: null,
});

const updatePricing = async (evt) => {
  if (!evt.name) {
    return;
  }

  if (evt.name == 'checkout.loaded') {
    const data = evt.data;

    currency_formatter = initCurrencyFormatter(data.currency_code);

    order_summary.value = {
      currency_code: data.currency_code,
      total: currency_formatter.format(data.totals.total),
      planName: data.items[0].product.name,
      planDuration: data.items[0].price_name,
      planDurationLong: 'annual subscription',
      quantity: 1,
      subtotal: currency_formatter.format(data.totals.subtotal),
      taxes: currency_formatter.format(data.totals.tax),
      dueToday: currency_formatter.format(data.totals.total),
      dueOnRenewal: currency_formatter.format(data.recurring_totals.total),
    }

  }

  console.log(evt);
}

const setupPaddle = async () => {
  const response = await fetch('/api/v1/subscription/paddle/info', {
    mode: 'same-origin',
    credentials: 'include',
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    }
  });

  const {
    paddle_environment: paddleEnvironment,
    paddle_plan_info: paddlePlanInfo,
    paddle_token: paddleToken
  } = await response.json();

  console.log(paddleEnvironment, paddlePlanInfo, paddleToken)

  let Paddle; // The initialized Paddle instance.

  const paddleItems = paddlePlanInfo.map((priceId) => ({
    quantity: 1,
    priceId,
  }));

  initializePaddle({
    environment: paddleEnvironment,
    token: paddleToken,
    eventCallback: updatePricing,
    checkout: {
      settings: {
        displayMode: "inline",
        frameTarget: "checkout-container",
        frameInitialHeight: 450,
        frameStyle: "width: 100%; min-width: 312px; background-color: transparent; border: none;",
        variant: "one-page",
      }
    }
  }).then((paddleInstance) => {
    if (!paddleInstance) {
      return;
    }
    Paddle = paddleInstance;

    // open checkout
    function openCheckout() {
      Paddle.Checkout.open({
        items: paddleItems,

      });
    }

    console.log("opening checkout");
    openCheckout();
  });
}

setupPaddle();
</script>

<script lang="ts">
export default {
  name: 'SubscribeView',
};
</script>

<template>
  <div class="manage-mfa-view">
    <card-container class="summary-card">
      <ul class="summary">
        <li class="summary__total-price">
          <h2>{{ order_summary.currency_code }}{{ order_summary.total }}</h2>
        </li>
        <li class="summary__plan-duration-long">{{ order_summary.planDurationLong }}</li>
        <li class="summary__plan_name">{{ order_summary.planName }}</li>
        <li class="summary__plan-duration">{{ order_summary.planDuration }}</li>
        <li aria-hidden="true">
          <visual-divider></visual-divider>
        </li>
        <li class="summary__total-amount">Qty: {{ order_summary.quantity }}</li>
        <li class="summary__line-item">
          <p>Subtotal</p>
          <p>{{ order_summary.currency_code }}{{ order_summary.subtotal }}</p>
        </li>
        <li aria-hidden="true">
          <visual-divider></visual-divider>
        </li>
        <li class="summary__line-item">
          <p>Taxes</p>
          <p>{{ order_summary.currency_code }}{{ order_summary.taxes }}</p>
        </li>
        <li class="summary__line-item">
          <p>Due today</p>
          <p>{{ order_summary.currency_code }}{{ order_summary.dueToday }}</p>
        </li>
        <li class="summary__line-item">
          <p>Due on ????</p>
          <p>{{ order_summary.currency_code }}{{ order_summary.dueOnRenewal }}</p>
        </li>
      </ul>
    </card-container>
    <card-container class="checkout-container">
      <h2>Payment</h2>
    </card-container>
  </div>
</template>

<style scoped>
.manage-mfa-view {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;
  width: 100%;

  .checkout-container {
    width: 50%;
  }

  .summary-card {
    width: 50%;
  }

  .summary {
    display: flex;
    flex-direction: column;
    gap: 16px;

    .summary__line-item {
      display: flex;
      justify-content: space-between;
    }
  }

  .manage-mfa-view-left-column {
    h2 {
      font-family: metropolis;
      font-size: 1.5rem;
      font-weight: 500;
      color: var(--colour-ti-highlight);
      margin-block-end: 1rem;
    }

    p {
      line-height: 1.32;
      color: var(--colour-ti-base);
      margin-block-end: 2rem;

      a {
        color: var(--colour-ti-highlight);
      }
    }
  }

  .manage-mfa-view-right-column {
    max-width: 345px;
  }
}


@media (min-width: 1024px) {
  .hidden-sm {
    display: block;
  }

  .divider {
    align-self: stretch;
    height: auto;
  }

  .manage-mfa-view {
    flex-direction: row;
    gap: 2rem;

    .manage-mfa-view-left-column {
      max-width: 567px;
    }
  }
}
</style>
