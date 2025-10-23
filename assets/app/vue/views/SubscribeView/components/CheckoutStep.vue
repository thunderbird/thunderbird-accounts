<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { VisualDivider } from '@thunderbirdops/services-ui';
import { initializePaddle } from '@paddle/paddle-js';
import CardContainer from '@/components/CardContainer.vue';
import { ref } from 'vue';

const { t } = useI18n();

const csrfToken = window._page.csrfToken;

const initCurrencyFormatter = (code: string) => {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: code,
  });
};

let currencyFormatter = initCurrencyFormatter('USD');
const planName = ref();

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

  if (evt.name == 'checkout.completed') {
    const data = evt.data;
    if (data.status === 'completed') {
      const response = await fetch('/api/v1/subscription/paddle/complete', {
        mode: 'same-origin',
        credentials: 'include',
        method: 'POST',
        body: JSON.stringify({
          transactionId: data.transaction_id,
        }),
        headers: {
          'X-CSRFToken': csrfToken,
        },
      });
      const responseData = await response.json();
      if (responseData) {
        // Send them home
        window.location.href = '/dashboard';
      }
    }
  }

  if (evt.name.indexOf('checkout.') === 0) {
    const data = evt.data;

    currencyFormatter = initCurrencyFormatter(data.currency_code);

    order_summary.value = {
      currency_code: data.currency_code,
      total: currencyFormatter.format(data.totals.total),
      planName: planName.value,
      planDuration: data.items[0].price_name,
      planDurationLong: t('views.subscribe.lineItems.annualLong').toLowerCase(),
      quantity: 1,
      subtotal: currencyFormatter.format(data.totals.subtotal),
      taxes: currencyFormatter.format(data.totals.tax),
      dueToday: currencyFormatter.format(data.totals.total),
      dueOnRenewal: currencyFormatter.format(data.recurring_totals.total),
    };
  }

  console.log(evt);
};

const setupPaddle = async () => {
  const response = await fetch('/api/v1/subscription/paddle/info', {
    mode: 'same-origin',
    credentials: 'include',
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  });

  const {
    paddle_environment: paddleEnvironment,
    paddle_plan_info: paddlePlanInfo,
    paddle_token: paddleToken,
    signed_user_id: signedUserId,
  } = await response.json();

  console.log(paddleEnvironment, paddlePlanInfo, paddleToken);

  let Paddle; // The initialized Paddle instance.

  // We'll just grab the first plan and use those prices (really it's just 1 price here)
  const paddleItems = paddlePlanInfo[0]['prices'].map((priceId) => ({
    quantity: 1,
    priceId,
  }));

  planName.value = paddlePlanInfo[0]['name'];

  initializePaddle({
    environment: paddleEnvironment,
    token: paddleToken,
    eventCallback: updatePricing,
    checkout: {
      settings: {
        displayMode: 'inline',
        frameTarget: 'checkout-container',
        frameInitialHeight: 450,
        frameStyle: 'width: 100%; min-width: 312px; background-color: transparent; border: none;',
        variant: 'one-page',
      },
    },
  }).then((paddleInstance) => {
    if (!paddleInstance) {
      return;
    }
    Paddle = paddleInstance;

    // open checkout
    function openCheckout() {
      Paddle.Checkout.open({
        items: paddleItems,
        customData: {
          signed_user_id: signedUserId,
        },
      });
    }

    openCheckout();
  });
};

setupPaddle();
</script>

<script lang="ts">
export default {
  name: 'CheckoutStep',
};
</script>

<template>
  <div class="subscribe-view">
    <h2>{{ t('views.subscribe.title') }}</h2>
    <div class="container">
      <card-container class="summary-card">
        <ul class="summary">
          <li class="summary__total-price">
            <h3>{{ order_summary.total }}</h3>
          </li>
          <li class="summary__plan-duration-long">{{ order_summary.planDurationLong }}</li>
          <li aria-hidden="true" class="visual-divider">
            <visual-divider></visual-divider>
          </li>
          <li class="summary__plan_name">{{ order_summary.planName }}</li>
          <li class="summary__plan-duration">{{ order_summary.planDuration }}</li>
          <li class="summary__total-amount">{{ t('views.subscribe.lineItems.quantity', [order_summary.quantity]) }}</li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.subtotal') }}</p>
            <p class="summary__cost-amount">{{ order_summary.subtotal }}</p>
          </li>
          <li aria-hidden="true" class="visual-divider">
            <visual-divider></visual-divider>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.taxes') }}</p>
            <p class="summary__cost-amount">{{ order_summary.taxes }}</p>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.dueOn', [t('views.subscribe.lineItems.today').toLowerCase()]) }}</p>
            <p class="summary__cost-amount">{{ order_summary.dueToday }}</p>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.dueOn', ['???']) }}</p>
            <p class="summary__cost-amount">{{ order_summary.dueOnRenewal }}</p>
          </li>
        </ul>
      </card-container>
      <card-container class="checkout-container">
        <h2>Payment</h2>
      </card-container>
    </div>
  </div>
</template>

<style scoped>
.subscribe-view {
  width: 100%;

  .container {
    width: 100%;
    gap: 1rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 1rem;
  }

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

    .summary__total-price {
      font-size: 1.5rem;
      flex-grow: 0;
      color: var(--colour-ti-base);
      margin-bottom: -1rem;
      font-weight: normal !important;
    }

    .summary__line-item {
      display: flex;
      justify-content: space-between;
      font-size: 0.875rem;
      line-height: 1.23;
      color: var(--colour-ti-secondary);
    }

    .summary__plan-duration-long {
      color: var(--colour-ti-muted);
      font-size: 0.688rem;
      line-height: 1.2;
    }

    .summary__plan_name {
      font-weight: 600;
      font-size: 1rem;
      line-height: 1.188rem;
      letter-spacing: 0.48px;
    }

    .summary__plan-duration {
      color: var(--colour-ti-muted);
      font-weight: bold;
      font-size: 0.75rem;
      line-height: 1rem;
    }

    .summary__total-amount {
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 0.48px;
      color: var(--colour-ti-secondary);
    }

    .summary__plan-duration {
      margin-top: -1rem;
    }

    .visual-divider {
      margin-top: -0.75rem;
    }

    .summary__cost-amount {
      color: var(--colour-ti-secondary);
      font-size: 0.813rem;
      font-weight: 600;
      letter-spacing: 0.39px;
    }
  }
}

@media (min-width: 1024px) {
  .subscribe-view {
    .container {
      flex-direction: row;
      gap: 2rem;
    }
  }
}
</style>
