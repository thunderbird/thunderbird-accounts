<template>
  <section>
    <slot />
  </section>
</template>

<style scoped>
section {
  background-color: var(--colour-neutral-base);
  padding: 2rem 1.5rem;
  border-radius: 1.5rem;
  box-shadow: 0.25rem 0.25rem 1rem 0 rgba(0, 0, 0, 0.04);
}
</style>