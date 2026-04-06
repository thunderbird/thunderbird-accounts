<script setup lang="ts">
import { PhPushPin, PhPushPinSimple } from '@phosphor-icons/vue';

withDefaults(defineProps<{
  dark?: boolean;
  padding?: 'small' | 'default';
  title?: string;
  subtitle?: string;
  isPinnable?: boolean;
  isPinned?: boolean;
}>(), {
  padding: 'default',
});

defineEmits<{
  (e: 'togglePinned'): void;
}>();
</script>

<template>
  <section :class="{
    'dark': dark,
    'padding-small': padding === 'small',
    'padding-default': padding === 'default',
  }">
    <header>
      <h2 v-if="title" :class="{ 'with-subtitle': !!subtitle }">{{ title }}</h2>

      <button v-if="isPinnable" @click="$emit('togglePinned')">
        <ph-push-pin v-if="isPinned" size="20" />
        <ph-push-pin-simple v-else size="20" />
      </button>
    </header>

    <p v-if="subtitle">{{ subtitle }}</p>

    <slot />
  </section>
</template>

<style scoped>
section {
  position: relative;
  background-color: var(--colour-neutral-base);
  border-radius: 1.5rem;
  box-shadow: 0.25rem 0.25rem 1rem 0 rgba(0, 0, 0, 0.04);
  width: 100%;

  header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    button {
      all: unset;
      cursor: pointer;
      display: flex;
      align-items: center;
      color: var(--colour-ti-secondary);
      flex-shrink: 0;

      &:hover {
        color: var(--colour-ti-base);
      }
    }
  }

  h2 {
    font-size: 1.5rem;
    font-weight: 500;
    font-family: metropolis;
    color: var(--colour-ti-highlight);
    margin-block-end: 1.5rem;

    &.with-subtitle {
      margin-block-end: 0.25rem;
    }
  }

  p {
    font-family: Inter;
    line-height: 1.32;
    margin-block-end: 1.5rem;
    color: var(--colour-ti-secondary);
  }

  &.dark {
    background-color: transparent;
    background-image: linear-gradient(to bottom left, #16395f 5%, #171b24 60%);
  }

  &.padding-small {
    padding: 1rem 1rem 1.5rem 1rem;
  }

  &.padding-default {
    padding: 2rem 1.5rem;
  }
}

@media (min-width: 1024px) {
  section {
    max-width: 968px;
    margin: 0 auto;
  }
}
</style>