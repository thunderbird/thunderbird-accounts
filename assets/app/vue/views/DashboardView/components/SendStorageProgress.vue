<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { formatBytes, formatStorageProgress } from '@/views/DashboardView/formatters';

// Types
import { SendStorageData } from '@/views/DashboardView/types';

// API
import { getSendStorageInfo } from '@/views/DashboardView/api';

const { t } = useI18n();

const errorMessage = ref<string>(null);
const sendStorage = ref<SendStorageData | null>(null);

const storageProgress = computed(() => {
  if (!sendStorage.value) return '0%';

  return formatStorageProgress(sendStorage.value.used, sendStorage.value.total);
});
const storageQuotaFormatted = computed(() => formatBytes(String(sendStorage.value?.total ?? 0)));
const usedQuotaFormatted = computed(() => formatBytes(String(sendStorage.value?.used ?? 0)));

onMounted(async () => {
  try {
    const data = await getSendStorageInfo();

    if (!data.success) {
      errorMessage.value = t('views.mail.sections.dashboard.welcomeHeader.sendErrorMessage');
      return;
    }

    sendStorage.value = data.sendStorage;

    errorMessage.value = null;
  } catch (_error) {
    errorMessage.value = t('views.mail.sections.dashboard.welcomeHeader.sendErrorMessage');
  }
});
</script>

<template>
  <div class="send-storage">
    <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">
      {{ errorMessage }}
    </notice-bar>

    <template v-if="sendStorage">
      <div class="send-storage-info">
        <p class="send-storage-name">{{ t('views.mail.sections.dashboard.welcomeHeader.sendStorage') }}</p>
        <p class="send-storage-used">
          {{ t('views.mail.sections.dashboard.welcomeHeader.storageOf', { used: usedQuotaFormatted, total: storageQuotaFormatted }) }}
        </p>
      </div>

      <div class="send-storage-progress">
        <div class="send-storage-progress-fill" :style="{ width: storageProgress }" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.send-storage {
  color: var(--colour-ti-secondary);
  width: 100%;
  margin-block-start: 0.75rem;

  .send-storage-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-block-end: 0.375rem;
    flex-wrap: wrap;

    .send-storage-name {
      font-family: metropolis;
      font-size: 1.25rem;
      line-height: 1.2;
    }

    .send-storage-used {
      font-family: Inter;
      font-size: 1rem;
      font-weight: 600;
    }
  }

  .send-storage-progress {
    width: 100%;
    height: 12px;
    border-radius: 64px;
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.1);
    background-color: rgba(0, 0, 0, 0.1);
    overflow: hidden;

    .send-storage-progress-fill {
      height: 100%;
      border-radius: 64px;
      box-shadow: inset 0 3px 3px 0 rgba(255, 255, 255, 0.2);
      background-image: linear-gradient(to right, #58c9ff 58%, #ae55f7 118%, #e247c4 118%);
    }
  }
}
</style>
