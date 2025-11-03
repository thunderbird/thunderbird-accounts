<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';

// Types
import type { SubscriptionData } from '../types';

// API
import { getSubscriptionPlanInfo, getSubscriptionPortalLink } from '../api';

// Utils
import { formatSubscriptionData } from '../utils';

const { t, n, d } = useI18n();

const errorText = ref<string>(null);
const isLoading = ref<boolean>(true);
const subscription = ref<SubscriptionData | null>(null);

const getSubscriptionInfo = async () => {
  isLoading.value = true;

  try {
    const data = await getSubscriptionPlanInfo();

    if (!data.success) {
      throw new Error(data.error || t('views.dashboard.yourCurrentSubscription.loadingError'));
    }

    subscription.value = formatSubscriptionData(data.subscription, n, t, d);
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : t('views.dashboard.yourCurrentSubscription.loadingError');
  } finally {
    isLoading.value = false;
  }
}

const navigateToSubscription = async () => {
  try {
    const { url } = await getSubscriptionPortalLink(); 
    window.open(url, '_blank');
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : t('views.dashboard.yourCurrentSubscription.portalLinkError');
  }
};

onMounted(() => {
  getSubscriptionInfo();
});
</script>

<template>
  <section>
    <h2>{{ t('views.dashboard.yourCurrentSubscription.yourCurrentSubscription') }}</h2>

    <div v-if="isLoading">
      <p>{{ t('views.dashboard.yourCurrentSubscription.loading') }}</p>
    </div>

    <card-container v-else-if="subscription" dark padding="small">
      <div class="card-container-inner">
        <h3>{{ subscription.name }}</h3>
        <p class="subscription-description">{{ subscription.description }}</p>
        <p class="subscription-price">
          <span class="subscription-price-amount">
            <span class="subscription-price-currency">{{ subscription.currency }}</span>
            {{ subscription.price }}
          </span>
          <span class="subscription-price-period">{{ subscription.period }}</span>
        </p>
        <template v-for="[key, value] in Object.entries(subscription.features)" :key="key">
          <div v-if="value" class="subscription-feature">
            <hr />
            <div class="subscription-feature-item">
              <span><strong>{{ value }}</strong></span>
              <span>{{ t(`views.dashboard.yourCurrentSubscription.${key}`) }}</span>
            </div>
          </div>
        </template>
      </div>

      <div class="footer">
        <p v-if="subscription.autoRenewal">
          {{ t('views.dashboard.yourCurrentSubscription.autoRenewsOn') }}
          <strong>{{ subscription.autoRenewal }}</strong>
        </p>

        <primary-button @click="navigateToSubscription">
          {{ t('views.dashboard.yourCurrentSubscription.manageSubscriptionButtonLabel') }}
        </primary-button>

        <p class="footer-text">
          {{ t('views.dashboard.yourCurrentSubscription.footerText') }}
        </p>
      </div>
    </card-container>

    <notice-bar :type="NoticeBarTypes.Critical" v-if="errorText">{{ errorText }}</notice-bar>
  </section>
</template>

<style scoped>
section {
  max-width: 345px;
  color: var(--colour-ti-secondary);
}

h2 {
  font-family: metropolis;
  font-size: 0.8125rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.39px;
  line-height: 1.2;
  margin-block-end: 1rem;
}

h3 {
  font-family: metropolis;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 1.28px;
  text-transform: uppercase;
  color: var(--colour-accent-blue);
  text-align: center;
  margin-block-end: 0.5rem;
}

.card-container-inner {
  border-radius: 1rem;
  border: solid 1px rgba(88, 201, 255, 0.2);
  background-color: rgba(0, 0, 0, 0.4);
  text-align: center;
  color: #eeeef0; /* TODO: --colour-ti-base forced dark */
  padding: 1rem;
  margin-block-end: 1rem;

  .subscription-description {
    font-size: 0.875rem;
    line-height: 1.23;
    color: #d9d9de; /* TODO: --colour-ti-secondary forced dark */
    margin-block-end: 0.75rem;
  }

  .subscription-price {
    font-family: metropolis;
    margin-block-end: 1.75rem;

    .subscription-price-amount {
      position: relative;
      font-size: 2rem;
      margin-inline-end: 0.375rem;
    }

    .subscription-price-period {
      font-family: Inter;
      font-size: 0.75rem;
    }

    .subscription-price-currency {
      position: absolute;
      top: 0.125rem;
      left: -0.875rem;
      font-size: 1.25rem;
      vertical-align: top;
    }
  }

  .subscription-feature {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0 1rem;
    font-size: 0.875rem;
    line-height: 1.23;

    &:not(:last-child) {
      margin-block-end: 0.75rem;
    }

    hr {
      height: 1px;
      color: #26292d;
    }

    .subscription-feature-item {
      display: flex;
      gap: 0.5ch;
      align-items: center;
    }
  }
}

.footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
  color: #eeeef0; /* TODO: --colour-ti-base forced dark */

  .footer-text {
    color: var(--colour-neutral-lower);
    font-size: 0.75rem;
    max-width: 75%;
  }
}
</style>