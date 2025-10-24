<script setup lang="ts">
import { computed, ref } from 'vue';
import { PhCaretDown } from '@phosphor-icons/vue';

const props = withDefaults(defineProps<{
  title: string;
  expandable?: boolean;
  defaultOpen?: boolean;
}>(), {
  expandable: true,
  defaultOpen: false,
});

const openInternal = ref<boolean>(props.defaultOpen);
const isOpen = computed<boolean>(() => props.expandable ? openInternal.value : true);

function toggle() {
  if (!props.expandable) {
    return;
  }

  openInternal.value = !openInternal.value;
}
</script>

<template>
  <section class="accordion">
    <button
      v-if="expandable"
      class="accordion__header"
      :class="{ 'open': isOpen }"
      type="button"
      :aria-expanded="isOpen ? 'true' : 'false'"
      @click="toggle"
    >
      <span class="accordion__left">
        <span v-if="$slots.icon" class="accordion__icon">
          <slot name="icon" />
        </span>
        <span class="accordion__title">{{ title }}</span>
      </span>
      <span class="accordion__chevron" :class="{ 'open': isOpen }" aria-hidden="true">
        <ph-caret-down size="20" />
      </span>
    </button>

    <div v-else class="accordion__header open">
      <span class="accordion__left">
        <span v-if="$slots.icon" class="accordion__icon">
          <slot name="icon" />
        </span>
        <span class="accordion__title">{{ title }}</span>
      </span>
    </div>

    <div v-show="isOpen" class="accordion__panel">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.accordion {
  width: 100%;

  .accordion__header {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    background-color: var(--colour-neutral-lower);
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
    padding: 1rem 0.5rem;
    text-align: left;
    color: var(--colour-ti-base);
    cursor: pointer;

    &.open {
      border-radius: 0.5rem 0.5rem 0 0;
    }

    &:focus-visible {
      outline: 2px solid var(--colour-ti-secondary);
      outline-offset: 2px;
    }

    .accordion__left {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .accordion__icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: #37adf9;
        width: 1.5rem;
        height: 1.5rem;
      }

      .accordion__title {
        font-family: metropolis;
        font-size: 1rem;
        font-weight: 500;
        line-height: 1.2;
        text-transform: capitalize;
        color: var(--colour-ti-base);
      }
    }

    .accordion__chevron {
      display: inline-flex;
      align-items: center;
      color: var(--colour-ti-base);
      width: 1.25rem;
      height: 1.25rem;
      margin-inline-end: 0.5rem;

      &.open {
        transform: rotate(180deg);
      }
    }
  }

  .accordion__panel {
    border: 1px solid var(--colour-neutral-border);
    border-top: none;
    border-radius: 0 0 0.5rem 0.5rem;
    padding: 1rem;
    background-color: var(--colour-neutral-base);
  }
}

/* Non-expandable header should not look clickable */
div.header {
  cursor: default;
}
</style>