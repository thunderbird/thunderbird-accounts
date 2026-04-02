<!-- TODO: This is a good candidate for a component in services-ui but since it's only used in this project, I kept it here for now. -->

<script setup lang="ts">
import { useId } from 'vue';
import type { SegmentedControlTab } from '../types';

const props = defineProps<{
  tabs: SegmentedControlTab[];
  modelValue: string;
  label: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const uid = useId();
const tabId = (id: string) => `${uid}-tab-${id}`;
const panelId = (id: string) => `${uid}-panel-${id}`;

function selectTab(id: string) {
  emit('update:modelValue', id);
}

function onTabKeydown(event: KeyboardEvent, index: number) {
  const count = props.tabs.length;
  let next: number | null = null;

  switch (event.key) {
    case 'ArrowRight':
      next = (index + 1) % count;
      break;
    case 'ArrowLeft':
      next = (index - 1 + count) % count;
      break;
    case 'Home':
      next = 0;
      break;
    case 'End':
      next = count - 1;
      break;
    default:
      return;
  }

  event.preventDefault();
  const tab = props.tabs[next];
  emit('update:modelValue', tab.id);
  document.getElementById(tabId(tab.id))?.focus();
}
</script>

<script lang="ts">
export default {
  name: 'SegmentedControlSlider',
};
</script>

<template>
  <div class="container">
    <div class="segmented-control" role="tablist" :aria-label="label">
      <button
        v-for="(tab, index) in tabs"
        :key="tab.id"
        :id="tabId(tab.id)"
        role="tab"
        :aria-selected="modelValue === tab.id"
        :aria-controls="panelId(tab.id)"
        :tabindex="modelValue === tab.id ? 0 : -1"
        :class="['tab-button', { active: modelValue === tab.id }]"
        @click="selectTab(tab.id)"
        @keydown="onTabKeydown($event, index)"
      >
        <component
          v-if="tab.icon"
          :is="tab.icon"
          :size="16"
          aria-hidden="true"
        />
        <span>{{ tab.label }}</span>
      </button>
    </div>
  
    <div
      v-for="tab in tabs"
      :key="tab.id"
      :id="panelId(tab.id)"
      role="tabpanel"
      :aria-labelledby="tabId(tab.id)"
      :hidden="modelValue !== tab.id"
      :tabindex="modelValue === tab.id ? 0 : undefined"
      class="tab-panel"
    >
      <slot :name="tab.id" />
    </div>
  </div>
</template>

<style scoped>
.container {
  flex: 1;
}

.segmented-control {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem;
  background-color: var(--colour-neutral-lower);
  border: 1px solid var(--colour-neutral-border);
  border-radius: 0.625rem;
}

.tab-button {
  all: unset;
  box-sizing: border-box;
  display: flex;
  flex: 1 0 0;
  align-items: center;
  justify-content: center;
  gap: 0.1875rem;
  min-width: 64px;
  height: 32px;
  padding: 0.5rem 0.75rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  font-family: Inter, sans-serif;
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.5;
  color: var(--colour-ti-muted);
  cursor: pointer;
  white-space: nowrap;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;

  &:focus-visible {
    outline: 2px solid var(--colour-primary-default);
    outline-offset: 2px;
  }

  &.active {
    background-color: var(--colour-neutral-base);
    border: 1px solid var(--colour-primary-default);
    box-shadow: 0 0 3px 0 rgba(0, 0, 0, 0.25);
    color: var(--colour-primary-default);
  }
}

.tab-panel {
  margin-block-start: 0.625rem;

  &:focus-visible {
    outline: 2px solid var(--colour-primary-default);
    outline-offset: 2px;
    border-radius: 4px;
  }
}
</style>
