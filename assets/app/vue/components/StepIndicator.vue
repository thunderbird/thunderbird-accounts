<script setup lang="ts">
import { PhCheckCircle } from '@phosphor-icons/vue';

export type StepIndicatorStep = {
  key: string;
  label: string;
};

defineProps<{
  steps: StepIndicatorStep[];
  currentStep: number;
  ariaLabel?: string;
}>();
</script>

<template>
  <nav class="step-indicator" :aria-label="ariaLabel">
    <ol>
      <li
        v-for="(step, index) in steps"
        :key="step.key"
        :class="{ active: index === currentStep, completed: index < currentStep }"
        :aria-current="index === currentStep ? 'step' : undefined"
      >
        <ph-check-circle size="24" :weight="index < currentStep ? 'fill' : 'regular'" aria-hidden="true" />
        <span>{{ step.label }}</span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.step-indicator {
  display: block;
  background-color: var(--colour-neutral-lower);
  border-radius: 0.5rem;
  padding: 1rem;

  ol {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  li {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: metropolis;
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: 0.65px;
    text-transform: uppercase;
    color: var(--colour-ti-secondary);

    &.active {
      color: var(--colour-primary-default);
    }

    /* Connector between steps (vertical on mobile) */
    &:not(:last-child)::after {
      content: '';
      position: absolute;
      inset-inline-start: 0.75rem;
      top: 100%;
      width: 1px;
      height: 0.75rem;
      background-color: var(--colour-neutral-border);
    }
  }
}

@media (min-width: 768px) {
  .step-indicator {
    display: inline-block;
    padding: 0.75rem 1.5rem;

    ol {
      flex-direction: row;
      align-items: center;
      gap: 0;
    }

    li {
      font-size: 0.875rem;

      /* Connector between steps (horizontal on desktop) */
      &:not(:last-child)::after {
        position: static;
        width: 2.5rem;
        height: 1px;
        margin-inline: 1rem;
      }
    }
  }
}
</style>
