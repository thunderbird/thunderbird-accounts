<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <div class="action-card">
    <div class="action-content">
      <div class="action-header">
        <slot name="icon" />
        <p class="action-title">{{ title }}</p>
      </div>
      <p class="action-description" v-if="description">{{ description }}</p>

      <slot />
    </div>

    <slot name="action" />
  </div>
</template>

<style scoped>
.action-card {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem 0.5rem 0.5rem;
  border: 1px solid var(--colour-neutral-border);
  border-radius: 8px;

  .action-content {
    display: flex;
    flex-direction: column;
    flex: 1 0 0;
    gap: 0.5rem;

    .action-header {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      color: var(--colour-ti-highlight);

      .action-title {
        flex: 1 0 0;
        font-family: Inter, sans-serif;
        font-size: 0.875rem;
        line-height: 1.23;
        color: var(--colour-ti-base);
      }
    }

    .action-description {
      font-family: Inter, sans-serif;
      font-size: 0.75rem;
      line-height: normal;
      color: var(--colour-ti-secondary);
    }
  }
}

</style>
