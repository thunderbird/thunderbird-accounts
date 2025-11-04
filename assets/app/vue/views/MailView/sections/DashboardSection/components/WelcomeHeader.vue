<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { formatBytes } from '@/views/DashboardView/utils';

// Types
import { SubscriptionData } from '@/views/DashboardView/types';

// API
import { getSubscriptionPlanInfo } from '@/views/DashboardView/api';

const { t } = useI18n();

const loading = ref(true);
const errorMessage = ref<string>(null);
const planInfo = ref<SubscriptionData | null>(null);

const planStorageProgress = computed(() => {
  if (!planInfo.value) return '0%';

  const usedQuota = parseFloat(planInfo.value?.usedQuota);
  const mailStorage = parseFloat(planInfo.value?.features.mailStorage);

  if (mailStorage === 0) {
    return '0%';
  }

  return `${(usedQuota / mailStorage) * 100}%`;
});
const mailStorageQuotaFormatted = computed(() => formatBytes(planInfo.value?.features.mailStorage));
const usedQuotaFormatted = computed(() => formatBytes(planInfo.value?.usedQuota));
const userEmail = computed(() => window._page?.userEmail);
const userDisplayName = computed(() => window._page?.userDisplayName);

onMounted(async () => {
  try {
    const data = await getSubscriptionPlanInfo();

    if (!data.success) {
      errorMessage.value = t('views.mail.sections.dashboard.welcomeHeader.errorMessage');
      return;
    }

    planInfo.value = data.subscription;

    errorMessage.value = null;
  } catch (_error) {
    errorMessage.value = t('views.mail.sections.dashboard.welcomeHeader.errorMessage');
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <header>
    <div class="welcome-container">
      <p class="welcome">{{ t('views.mail.sections.dashboard.welcomeHeader.welcome') }},</p>
      <p class="name">{{ userDisplayName }}</p>
      <p class="email">{{ userEmail }}</p>
    </div>

    <div class="plan-info-container">
      <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">
        {{ errorMessage }}
      </notice-bar>

      <template v-if="planInfo">
        <div class="plan-info">
          <p class="plan-name">{{ planInfo.name }}</p>
          <p class="plan-storage">
            {{ t('views.mail.sections.dashboard.welcomeHeader.storageOf', { used: usedQuotaFormatted, total: mailStorageQuotaFormatted }) }}
          </p>
        </div>

        <div class="plan-storage-progress">
          <div class="plan-storage-progress-fill" :style="{ width: planStorageProgress }" />
        </div>
      </template>
    </div>
  </header>
</template>

<style scoped>
header {
  display: grid;
  grid-template-columns: 1fr;
  grid-auto-flow: row;
  row-gap: 2rem;
  column-gap: 1.6875rem;
  align-items: end;
  margin-block-end: 2.625rem;
}

.welcome-container {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-family: metropolis;

  .welcome {
    text-transform: uppercase;
    font-size: 0.875rem;
    letter-spacing: 0.42px;
    color: var(--colour-ti-muted);
  }

  .name {
    font-size: 2.25rem;
    line-height: 1.2;
    letter-spacing: -0.36px;
    color: var(--colour-ti-base);
  }

  .email {
    font-family: Inter;
    font-size: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
  }
}

.plan-info-container {
  color: var(--colour-ti-secondary);
  width: 100%;
  margin-block-end: 0.5rem;

  .plan-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-block-end: 0.53rem;
    flex-wrap: wrap;

    .plan-name {
      font-family: metropolis;
      font-size: 1.25rem;
      line-height: 1.2;
    }

    .plan-storage {
      font-family: Inter;
      font-size: 1rem;
      font-weight: 600;
    }
  }

  .plan-storage-progress {
    width: 100%;
    height: 12px;
    border-radius: 64px;
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.1);
    background-color: rgba(0, 0, 0, 0.1);
    overflow: hidden;

    .plan-storage-progress-fill {
      height: 100%;
      border-radius: 64px;
      box-shadow: inset 0 3px 3px 0 rgba(255, 255, 255, 0.2);
      background-image: linear-gradient(to right, #58c9ff 58%, #ae55f7 118%, #e247c4 118%);
    }
  }
}

@media (min-width: 1024px) {
  header {
    grid-template-columns: 1fr 1fr;
  }
}
</style>