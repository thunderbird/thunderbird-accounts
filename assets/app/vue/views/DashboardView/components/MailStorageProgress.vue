<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { formatBytes, formatStorageProgress } from '@/views/DashboardView/formatters';

// Types
import { SubscriptionData } from '@/views/DashboardView/types';

// API
import { getSubscriptionPlanInfo } from '@/views/DashboardView/api';

const { t } = useI18n();

const errorMessage = ref<string>(null);
const planInfo = ref<SubscriptionData | null>(null);

const storageProgress = computed(() => {
  if (!planInfo.value) return '0%';

  return formatStorageProgress(parseFloat(planInfo.value.usedQuota), parseFloat(planInfo.value.features.mailStorage));
});
const storageQuotaFormatted = computed(() => formatBytes(planInfo.value?.features.mailStorage));
const usedQuotaFormatted = computed(() => formatBytes(planInfo.value?.usedQuota));

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
  }
});
</script>

<template>
  <div class="mail-storage">
    <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">
      {{ errorMessage }}
    </notice-bar>

    <template v-if="planInfo">
      <div class="mail-storage-info">
        <p class="plan-name">{{ t('views.mail.sections.dashboard.welcomeHeader.mailStorage') }}</p>
        <p class="plan-storage">
          {{ t('views.mail.sections.dashboard.welcomeHeader.storageOf', { used: usedQuotaFormatted, total: storageQuotaFormatted }) }}
        </p>
      </div>

      <div class="mail-storage-progress">
        <div class="mail-storage-progress-fill" :style="{ width: storageProgress }" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.mail-storage {
  width: 100%;

  .mail-storage-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-block-end: 0.375rem;
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

  .mail-storage-progress {
    width: 100%;
    height: 12px;
    border-radius: 64px;
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.1);
    background-color: rgba(0, 0, 0, 0.1);
    overflow: hidden;

    .mail-storage-progress-fill {
      height: 100%;
      border-radius: 64px;
      box-shadow: inset 0 3px 3px 0 rgba(255, 255, 255, 0.2);
      background-image: linear-gradient(to right, #58c9ff 58%, #ae55f7 118%, #e247c4 118%);
    }
  }
}
</style>
