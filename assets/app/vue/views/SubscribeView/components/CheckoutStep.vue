<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { LoadingSkeleton, NoticeBar, NoticeBarTypes, VisualDivider } from '@thunderbirdops/services-ui';
import { initializePaddle, PaddleEventData } from '@paddle/paddle-js';
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
let paddle = null;

const planName = ref();
const planSystemError = ref(false);
const paymentComplete = ref(false);
const paddleLoading = ref(true);
const paddleUnknownError = ref(false);

// Placeholder information for the skeletons
const order_summary = ref({
  currency_code: 'USD',
  total: 'US$000.00',
  planName: 'Placeholder plan name',
  planDuration: null,
  planDurationLong: null,
  quantity: 1,
  subtotal: 'US$000.00',
  taxes: 'US$000.00',
  dueToday: 'US$000.00',
  dueOnRenewal: 'US$000.00',
});

/**
 * "Open" the checkout, which just really involves passing Paddle some settings for the iframe that is loaded inline.
 * Here we'll set the checkout product (paddleItems) and the signed user id which will be used to track the transaction.
 * @param paddleItems
 * @param signedUserId
 */
const openCheckout = (paddleItems: any, signedUserId: string) => {
  paddle.Checkout.open({
    items: paddleItems,
    customData: {
      // This will tie the transaction and subscription to our user uuid
      signed_user_id: signedUserId,
    },
  });
};

/**
 * Callback to handle Paddle checkout events
 * We use this to update our cart with real data as the user clicks and types around the Paddle checkout iframe.
 * Additionally on dev we need to keep a copy of the transaction id so we can later look it up and manually run the
 * webhook call to activate subscription features, as we cannot get webhooks locally.
 * @param evt
 */
const onPaddleEvent = async (evt: PaddleEventData) => {
  if (evt?.name == 'checkout.completed') {
    paymentComplete.value = true;
    return;
  }

  if (!evt?.name || !evt?.data) {
    return;
  }

  // Just update the cart, every checkout.* event has all the information on it.
  if (evt.name.indexOf('checkout.') === 0) {
    const data = evt.data;

    // Set the transaction id if we're on a dev build
    if (import.meta.env.DEV && data?.transaction_id) {
      await fetch('/api/v1/subscription/paddle/txid/', {
        mode: 'same-origin',
        credentials: 'include',
        method: 'PUT',
        body: JSON.stringify({
          txid: data?.transaction_id,
        }),
        headers: {
          'X-CSRFToken': csrfToken,
        },
      });
    }

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
    paddleLoading.value = false;
  }
};

/**
 * Retrieve the paddle info (environment, plans, client token, and signed user id) and initialize the paddle checkout
 * module.
 */
const setupPaddle = async () => {
  const response = await fetch('/api/v1/subscription/paddle/info/', {
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

  if (paddlePlanInfo.length === 0) {
    planSystemError.value = true;
  }

  // We'll just grab the first plan and use those prices (really it's just 1 price here)
  const paddleItems = paddlePlanInfo[0]['prices'].map((priceId) => ({
    quantity: 1,
    priceId,
  }));

  planName.value = paddlePlanInfo[0]['name'];

  initializePaddle({
    environment: paddleEnvironment,
    token: paddleToken,
    eventCallback: onPaddleEvent,
    checkout: {
      settings: {
        // Must be a full url
        successUrl: `${window.location.origin}/subscription/paddle/complete/`,
        displayMode: 'inline',
        frameTarget: 'checkout-container',
        frameInitialHeight: 992,
        frameStyle: 'width: 100%; min-width: 312px; background-color: transparent; border: none;',
        variant: 'one-page',
      },
    },
  }).then((paddleInstance) => {
    if (!paddleInstance) {
      console.error('Could not retrieve the paddle instance', paddleInstance);
      paddleUnknownError.value = true;
      return;
    }
    // Set the component-wide paddle object
    paddle = paddleInstance;
    openCheckout(paddleItems, signedUserId);
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
    <notice-bar v-if="paddleUnknownError" :type="NoticeBarTypes.Critical">{{
      t('views.subscribe.paddleUnknownError')
    }}</notice-bar>
    <notice-bar v-if="planSystemError" :type="NoticeBarTypes.Critical">{{
      t('views.subscribe.planSystemError')
    }}</notice-bar>
    <div class="container">
      <card-container class="summary-card">
        <ul class="summary">
          <li class="summary__total-price">
            <loading-skeleton :is-loading="paddleLoading">
              <h3>{{ order_summary.total }}</h3>
            </loading-skeleton>
          </li>
          <li class="summary__plan-duration-long">
            <loading-skeleton :is-loading="paddleLoading">
              {{ order_summary.planDurationLong }}
            </loading-skeleton>
          </li>
          <li aria-hidden="true" class="visual-divider">
            <visual-divider></visual-divider>
          </li>
          <li class="summary__plan_name">
            <loading-skeleton :is-loading="paddleLoading">
              {{ order_summary.planName }}
            </loading-skeleton>
          </li>
          <li class="summary__plan-duration">
            <loading-skeleton :is-loading="paddleLoading">
              {{ order_summary.planDuration }}
            </loading-skeleton>
          </li>
          <li class="summary__total-amount">
            <loading-skeleton :is-loading="paddleLoading">
              {{ t('views.subscribe.lineItems.quantity', [order_summary.quantity]) }}
            </loading-skeleton>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.subtotal') }}</p>
            <p class="summary__cost-amount">
              <loading-skeleton :is-loading="paddleLoading">
                {{ order_summary.subtotal }}
              </loading-skeleton>
            </p>
          </li>
          <li aria-hidden="true" class="visual-divider">
            <visual-divider></visual-divider>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.taxes') }}</p>
            <p class="summary__cost-amount">
              <loading-skeleton :is-loading="paddleLoading">
                {{ order_summary.taxes }}
              </loading-skeleton>
            </p>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.dueOn', [t('views.subscribe.lineItems.today').toLowerCase()]) }}</p>
            <p class="summary__cost-amount">
              <loading-skeleton :is-loading="paddleLoading">
                {{ order_summary.dueToday }}
              </loading-skeleton>
            </p>
          </li>
          <li class="summary__line-item">
            <p>{{ t('views.subscribe.lineItems.dueOn', [t('views.subscribe.lineItems.renewal').toLowerCase()]) }}</p>
            <p class="summary__cost-amount">
              <loading-skeleton :is-loading="paddleLoading">
                {{ order_summary.dueOnRenewal }}
              </loading-skeleton>
            </p>
          </li>
        </ul>
      </card-container>
      <card-container class="checkout-container">
        <h3>{{ t('views.subscribe.checkoutHeading') }}</h3>
        <!-- Paddle's checkout will just disappear into the void once it starts redirecting us to successUrl.
             It looks ugly, so show a small message in its place. -->
        <p v-if="paymentComplete">{{ t('views.subscribe.paymentComplete') }}</p>
      </card-container>
    </div>
  </div>
</template>

<style scoped>
.subscribe-view {
  width: 100%;

  /* Used in the notice-bar component */
  .notice-bar {
    margin-bottom: 1rem;
  }

  .container {
    width: 100%;
    gap: 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
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
    width: 100%;
    max-width: 60%;
  }

  .summary-card {
    width: 100%;
    max-width: 60%;
    min-height: 340px;
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
      align-items: flex-start;
      flex-direction: row;
      gap: 2rem;
    }
  }
}
</style>
