<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { initializePaddle, type Environments } from '@paddle/paddle-js';
import { NOT_INTERESTED_SURVEY_LINK } from '@/defines';
import PlanCard from '@/components/PlanCard.vue';
import { i18n } from '@/composables/i18n';
import { useI18n } from 'vue-i18n';
import SignUpLayout from '../../components/SignUpLayout.vue';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';

const DEFAULT_MONTHLY_PRICE = '$6';

const { t } = useI18n();

const signUpFlowStore = useSignUpFlowStore();
const { nextStep } = signUpFlowStore;

const planName = ref(window._page?.planInfo?.name ?? '');
const planDescription = ref(window._page?.planInfo?.description ?? '');
const priceDisplay = ref(DEFAULT_MONTHLY_PRICE);
const priceLoading = ref(true);
const priceError = ref<string | null>(null);

const formatLocalizedMonthlyPrice = (
  amountCents: string,
  currency: string,
  billingInterval: string | undefined
): string => {
  let price = parseFloat(amountCents) / 100;

  if (billingInterval?.toLowerCase() === 'year') {
    price = price / 12;
  }

  const fractionDigits = Number.isInteger(price) ? 0 : 2;

  return new Intl.NumberFormat(i18n.locale.value, {
    style: 'currency',
    currency,
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(price);
};

const loadPlanPrice = async () => {
  const planInfo = window._page?.planInfo;
  const paddleToken = window._page?.paddleToken;
  const paddleEnvironment = window._page?.paddleEnvironment;

  if (!planInfo?.prices?.length || !paddleToken) {
    priceLoading.value = false;
    priceError.value = t('views.mail.views.signUp.stepConfirmPlan.planInfoError');
    return;
  }

  try {
    const paddle = await initializePaddle({
      environment: paddleEnvironment as Environments,
      token: paddleToken,
    });

    if (!paddle) {
      priceError.value = t('views.mail.views.signUp.stepConfirmPlan.paddleError');
      return;
    }

    const preview = await paddle.PricePreview({
      items: planInfo.prices.map((priceId) => ({
        quantity: 1,
        priceId,
      })),
    });

    const lineItem = preview.data.details.lineItems[0];
    if (lineItem) {
      priceDisplay.value = formatLocalizedMonthlyPrice(
        lineItem.totals.total,
        preview.data.currencyCode,
        lineItem.price.billingCycle?.interval
      );
    }
  } catch (error) {
    priceError.value = t('views.mail.views.signUp.stepConfirmPlan.paddleError', {
      error: error instanceof Error ? error.message : String(error),
    });
  } finally {
    priceLoading.value = false;
  }
};

const onNotInterested = () => {
  window.location.href = NOT_INTERESTED_SURVEY_LINK;
};

const onSubmit = () => {
  nextStep();
};

onMounted(() => {
  loadPlanPrice();
});
</script>

<script lang="ts">
export default {
  name: 'StepConfirmPlan',
};
</script>

<template>
  <sign-up-layout
    step-id="step-confirm-plan"
    :title="$t('views.mail.views.signUp.stepConfirmPlan.title')"
    :subtitle="$t('views.mail.views.signUp.stepConfirmPlan.subtitle')"
    :submit-disabled="priceLoading"
    :submit-title="$t('views.mail.views.signUp.stepConfirmPlan.action')"
    :show-alternative-action="true"
    :alternative-action-title="$t('views.mail.views.signUp.stepConfirmPlan.notInterested')"
    @alternative-action="onNotInterested"
    @submit="onSubmit"
  >
    <template v-slot:notice-bars>
      <slot name="notice-bars">
        <notice-bar :type="NoticeBarTypes.Critical" v-if="priceError">
          {{ priceError }}
        </notice-bar>
      </slot>
    </template>
    <template v-slot:form-elements>
      <div class="plan-card-container">
        <plan-card
          :name="planName"
          :description="planDescription"
          :price="priceDisplay"
          :price-loading="priceLoading"
        />
      </div>
    </template>
  </sign-up-layout>
</template>

<style scoped>
.plan-card-container {
  margin-block-end: 1rem;
}
</style>
