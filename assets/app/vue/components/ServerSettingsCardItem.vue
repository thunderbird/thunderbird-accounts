<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCopySimple, PhDatabase, PhShieldCheck } from '@phosphor-icons/vue';

export type ServerSettingsDetails = {
  protocol: string;
  server: string;
  port: string;
};

defineProps<{
  title: string;
  details: ServerSettingsDetails;
}>();

const { t } = useI18n();
const copyError = ref('');
let copyErrorTimer: ReturnType<typeof setTimeout> | undefined;

const copyValue = async (value: string | number) => {
  copyError.value = '';
  clearTimeout(copyErrorTimer);

  try {
    await navigator.clipboard.writeText(String(value));
  } catch (_err) {
    copyError.value = t('components.serverSettingsCardItem.copyError');
    copyErrorTimer = setTimeout(() => { copyError.value = ''; }, 4000);
  }
};
</script>

<template>
  <div class="server-settings-card">
    <header>
      <slot name="icon" />
      <span>{{ title }}</span>
    </header>

    <slot name="tabs" />

    <div class="server-detail-item">
      <div class="server-detail-item-label">
        <ph-database size="16" />
        <strong>{{ t('views.mail.sections.dashboard.server') }}</strong>
      </div>
      <div class="server-detail-item-value">
        <span>{{ details.server }}</span>
        <button type="button" class="copy-btn" @click="copyValue(details.server)" :aria-label="t('views.mail.sections.dashboard.copyServer')">
          <ph-copy-simple size="12" />
        </button>
      </div>
    </div>

    <div class="server-detail-item">
      <div class="server-detail-item-label">
        <ph-shield-check size="16" />
        <strong>{{ t('views.mail.sections.dashboard.port') }}</strong>
      </div>
      <div class="server-detail-item-value">
        <span>{{ details.port }}</span>
        <button type="button" class="copy-btn" @click="copyValue(details.port)" :aria-label="t('views.mail.sections.dashboard.copyPort')">
          <ph-copy-simple size="12" />
        </button>
      </div>
    </div>

    <p v-if="copyError" class="copy-error" role="alert">{{ copyError }}</p>

    <slot name="footer" />
  </div>
</template>

<style scoped>
.server-settings-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.server-settings-card header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.375rem;
  background-color: var(--colour-primary-soft);
  border-radius: 0.1875rem;
  padding: 0.1875rem;
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--colour-ti-base);
  letter-spacing: 0.42px;
}

.server-settings-card :deep(.incoming-server-tabs) {
  display: flex;
  flex-direction: row;
}

.server-settings-card :deep(.incoming-server-tab) {
  padding-block: 0.5rem;
  font-size: 0.6875rem;
  font-family: Inter;
  color: var(--colour-ti-base);
  width: 100%;
  border: none;
  border-block-end: 2px solid transparent;
  background-color: transparent;
  cursor: pointer;
}

.server-settings-card :deep(.incoming-server-tab.active) {
  border-block-end: 2px solid var(--colour-ti-highlight);
}

.server-settings-card :deep(.incoming-server-tab:not(.active)) {
  color: var(--colour-ti-muted);
  background-color: var(--colour-neutral-lower);
}

.server-settings-card .server-detail-item {
  display: flex;
  align-items: center;
  padding: 0.25rem 0.375rem;
  color: var(--colour-ti-secondary);
  font-size: 0.75rem;

  .server-detail-item-label {
    display: flex;
    align-items: center;
    flex: 1;
    gap: 0.1875rem;
  }

  .server-detail-item-value {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  strong {
    font-size: 0.6875rem;
  }
}

.server-settings-card .copy-error {
  color: var(--colour-danger-default);
  font-size: 0.75rem;
  padding: 0.25rem 0.375rem;
  margin: 0;
}

.server-settings-card .copy-btn {
  background: none;
  border: none;
  padding: 0.25rem 0.38rem;
  margin: 0;
  color: inherit;
  cursor: pointer;
}

.server-settings-card .copy-btn:hover {
  color: var(--colour-primary-hover);
}

.server-settings-card .copy-btn:active {
  color: var(--colour-primary-pressed);
}

.server-settings-card :deep(.what-is-container) {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-grow: 0;
  gap: 0.25rem;
  cursor: pointer;
  text-decoration: none;
  width: max-content;
  color: var(--colour-ti-base);

  a {
    color: var(--colour-ti-highlight);
  }
}

/* Fills the gap between the trigger row and the tooltip so :hover is not lost in dead space */
.server-settings-card :deep(.what-is-container::before) {
  content: '';
  position: absolute;
  bottom: 100%;
  left: 50%;
  width: max(100%, 18rem);
  height: 0.75rem;
  transform: translateX(-50%);
}

.server-settings-card :deep(.what-is-container .tooltip) {
  visibility: hidden;
  opacity: 0;
  width: max-content;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  top: auto;
  transform: translateX(-50%);
}

.server-settings-card :deep(.what-is-container:hover .tooltip),
.server-settings-card :deep(.what-is-container .tooltip:hover) {
  visibility: visible;
  opacity: 1;
  cursor: default;
}

.server-settings-card :deep(.what-is-container span) {
  color: var(--colour-ti-muted);
  font-size: 0.75rem;
}
</style>
