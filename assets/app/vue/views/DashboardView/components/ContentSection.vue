<script setup lang="ts">

</script>

<template>
<section class="content-section">
  <slot/>
</section>
</template>

<style scoped>
.content-section {
  align-self: stretch;
  flex-grow: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;

  padding: 32px 24px;
  border-radius: 24px;
  box-shadow: 4px 4px 16px 0 rgba(0, 0, 0, 0.04);
  background-color: var(--colour-neutral-base);
}
</style>
