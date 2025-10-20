<script setup lang="ts">

withDefaults(defineProps<{
  dark?: boolean;
  padding?: 'small' | 'default';
}>(), {
  padding: 'default',
});
</script>

<template>
  <section :class="{
    'dark': dark,
    'padding-small': padding === 'small',
    'padding-default': padding === 'default',
  }">
    <slot />
  </section>
</template>

<style scoped>
section {
  background-color: var(--colour-neutral-base);
  border-radius: 1.5rem;
  box-shadow: 0.25rem 0.25rem 1rem 0 rgba(0, 0, 0, 0.04);

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
</style>