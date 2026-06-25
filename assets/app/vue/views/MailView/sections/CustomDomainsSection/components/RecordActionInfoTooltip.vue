<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhInfo } from '@phosphor-icons/vue';
import { ToolTip } from '@thunderbirdops/services-ui';

import type { RowAction } from '../types';

const props = defineProps<{
  recordType: string;
  action: RowAction;
}>();

const { t, te } = useI18n();
const triggerRef = ref<HTMLElement | null>(null);
const isVisible = ref(false);

const containsTarget = (target: EventTarget | null) =>
  target instanceof Node && triggerRef.value?.contains(target);

const showTooltip = () => {
  isVisible.value = true;
};

const hideTooltip = (event: MouseEvent) => {
  if (!containsTarget(event.relatedTarget)) {
    isVisible.value = false;
  }
};

const info = computed(() => {
  const category = props.recordType === 'MX' ? 'MX' : props.recordType === 'SRV' ? 'SRV' : 'OTHER';
  const baseKey = `views.mail.sections.customDomains.recordActionInfo.${category}.${props.action}`;
  const hasLink = te(`${baseKey}.link`);
  const boldLabel = t(`${baseKey}.${props.action}`);
  const linkLabel = hasLink ? t(`${baseKey}.link`) : '';

  return {
    contentKey: `${baseKey}.content`,
    boldLabel,
    linkLabel,
    hasLink,
    alt: t(`${baseKey}.content`, { bold: boldLabel, link: linkLabel }),
  };
});
</script>

<template>
  <span
    ref="triggerRef"
    class="action-info-tooltip-trigger"
    :class="{ 'is-visible': isVisible }"
    @mouseleave="hideTooltip"
  >
    <span class="action-info-icon-trigger" @mouseenter="showTooltip">
      <ph-info size="16" class="action-info-icon" aria-hidden="true" />
    </span>
    <tool-tip :alt="info.alt">
      <i18n-t :keypath="info.contentKey" tag="span">
        <template #bold>
          <strong>{{ info.boldLabel }}</strong>
        </template>
        <template v-if="info.hasLink" #link>
          <!-- TODO: Replace with the actual support URL once we have one. -->
          <a href="https://support.tb.pro/" target="_blank">{{ info.linkLabel }}</a>
        </template>
      </i18n-t>
    </tool-tip>
  </span>
</template>

<style scoped>
.action-info-tooltip-trigger {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}

.action-info-icon-trigger {
  position: relative;
  display: inline-flex;
  cursor: pointer;

  &::before {
    content: '';
    position: absolute;
    bottom: 100%;
    left: 0;
    width: 100%;
    height: 0.5rem;
  }
}

.action-info-icon {
  color: var(--colour-ti-warning);
}

.action-info-tooltip-trigger :deep(.tooltip) {
  visibility: hidden;
  opacity: 0;
  width: max-content;
  max-width: 18rem;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  top: auto;
  transform: translateX(-50%);
  font-size: 0.8125rem;
  white-space: normal;
}

.action-info-tooltip-trigger.is-visible :deep(.tooltip) {
  visibility: visible;
  opacity: 1;
  cursor: default;
}

.action-info-tooltip-trigger :deep(.tooltip a) {
  color: var(--colour-ti-secondary);
}
</style>
