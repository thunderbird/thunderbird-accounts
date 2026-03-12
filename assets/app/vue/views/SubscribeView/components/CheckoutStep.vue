<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { LoadingSkeleton, NoticeBar, NoticeBarTypes, VisualDivider } from '@thunderbirdops/services-ui';
import { initializePaddle, PaddleEventData, CheckoutEventNames } from '@paddle/paddle-js';
import CardContainer from '@/components/CardContainer.vue';
import { onUnmounted, ref } from 'vue';

const { t } = useI18n();

const csrfToken = window._page.csrfToken;

const initCurrencyFormatter = (code: string) => {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: code,
  });
};

const DEFAULT_PAYMENT_TYPE = 'card';
const ARE_WE_DONE_YET_TIMER_MS = 2500;
const SHORT_WAIT_MS = 2500;
const EXCEPTIONS_UNTIL_ERROR_SHOWN = 3;

// We don't need these to be reactive
let currencyFormatter = initCurrencyFormatter('USD');
let paddle = null;
let doneCheckerHandler = null;
let exceptionCounter = 0;
let transactionId = null;
let paymentType = DEFAULT_PAYMENT_TYPE;

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
 * Clear the done checker handler in case we navigate away from the page
 */
onUnmounted(() => {
  if (doneCheckerHandler) {
    window.clearTimeout(doneCheckerHandler);
    doneCheckerHandler = null;
  }
})

/**
 * Work-around for Paddle's checkout.completed event not working with PayPal checkouts, 
 * and their successUrl not working as intended...
 * 
 * Poll the is-done api route every 2.5 seconds, and if we're doneish (paid or complete) 
 * then reload the window to let the payment verification screen do their magic.
 * 
 * Triggered by PaddleJS's checkout events. (Anyone with a transaction ID!)
 */
const areWeDoneHere = async () => {
  try {
    const response = await fetch('/api/v1/subscription/paddle/tx/is-done/', {
      mode: 'same-origin',
      credentials: 'include',
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });
    const data = await response.json();
    const { status } = data;

    // For some reason PaddleJS has paid's constant as undefined. Hmmm...
    if (['completed', 'paid'].indexOf(status) > -1) {
      // Remove the Paddle checkout form, and after a short wait reload the page.
      paymentComplete.value = true;
    }

    if (status === 'completed') {
      // We re-use this handler since it's not currently used, and it's hooked up to unMount.
      doneCheckerHandler = window.setTimeout(() => {
        window.location.reload();
      }, SHORT_WAIT_MS);
      return;
    }

    // Lastly clear up the exception counter, if we've reached here there's no exceptions happening and no errors need to be shown.
    exceptionCounter = 0;
  } catch (e) {
    console.error("Error checking done status: ", e);
    exceptionCounter++;
  }

  // If this occurs a few times in a row we should show an error
  if (exceptionCounter >= EXCEPTIONS_UNTIL_ERROR_SHOWN) {
    paddleUnknownError.value = true;
  } else {
    paddleUnknownError.value = false;
  }

  doneCheckerHandler = window.setTimeout(() => areWeDoneHere(), ARE_WE_DONE_YET_TIMER_MS);
}

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
  if (evt?.name == CheckoutEventNames.CHECKOUT_COMPLETED) {
    paymentComplete.value = true;
    return;
  }

  if (!evt?.name || !evt?.data) {
    return;
  }

  // Just update the cart, every checkout.* event has all the information on it.
  if (evt.name.indexOf('checkout.') === 0) {
    const data = evt.data;
    const backendNeedsUpdate = transactionId !== (data?.transaction_id ?? null) || paymentType !== data.payment.method_details.type;

    // Transaction ID should only update if we're not falsey.
    if (data?.transaction_id) {
      transactionId = data?.transaction_id ?? null;
    }

    // Payment type is only reliably updated on payment selected.
    if (evt.name == 'checkout.payment.selected') {
      paymentType = data.payment.method_details.type;
    }

    if (backendNeedsUpdate) {
      await fetch('/api/v1/subscription/paddle/tx/set/', {
        mode: 'same-origin',
        credentials: 'include',
        method: 'PUT',
        body: JSON.stringify({
          payment_type: paymentType,
          txid: transactionId,
        }),
        headers: {
          'X-CSRFToken': csrfToken,
        },
      });
    }

    if (!doneCheckerHandler && transactionId) {
      // Setup our done checker
      doneCheckerHandler = window.setTimeout(() => areWeDoneHere(), ARE_WE_DONE_YET_TIMER_MS);
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
        successUrl: `${window.location.origin}/subscription/paddle/complete/`,
        displayMode: 'inline',
        frameTarget: 'paddle-checkout',
        frameInitialHeight: 992,
        frameStyle: 'width: 100%; background-color: transparent; border: none;',
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
        <div v-else class="paddle-checkout"></div>
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
    min-height: 1090px;
  }

  .summary-card {
    width: 100%;
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

    .checkout-container {
      max-width: 60%;
    }

    .summary-card {
      max-width: 60%;
    }
  }
}
</style>
