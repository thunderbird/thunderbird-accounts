<script setup lang="ts">
import { ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';

import GenericModal from '@/components/GenericModal.vue';
import { getAppleMailQrCode } from '@/views/DashboardView/api';

const { t } = useI18n();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');
const svgSrc = ref<string | null>(null);
const loading = ref(false);
const errorMessage = ref<string | null>(null);

const fetchQrCode = async () => {
  loading.value = true;
  errorMessage.value = null;
  svgSrc.value = null;

  try {
    svgSrc.value = await getAppleMailQrCode();
  } catch (_error) {
    errorMessage.value = t('views.mail.sections.dashboard.appleMailQrModal.errorMessage');
  } finally {
    loading.value = false;
  }
};

defineExpose({
  open: () => {
    genericModal.value.open();
    fetchQrCode();
  },
});
</script>

<template>
  <generic-modal ref="genericModal" :title="t('views.mail.sections.dashboard.appleMailQrModal.title')">
    <p>{{ t('views.mail.sections.dashboard.appleMailQrModal.description') }}</p>
    <div v-if="loading" class="loading">
      {{ t('views.mail.sections.dashboard.appleMailQrModal.loading') }}
    </div>
    <p v-else-if="errorMessage" class="error">{{ errorMessage }}</p>
    <img
      v-else-if="svgSrc"
      :src="svgSrc"
      :alt="t('views.mail.sections.dashboard.appleMailQrModal.qrCodeAltDescription')"
    />
  </generic-modal>
</template>

<style scoped>
img {
  max-width: 300px;
}

.loading {
  padding: 2rem;
  color: var(--colour-ti-secondary);
}

.error {
  color: var(--colour-danger);
}
</style>
