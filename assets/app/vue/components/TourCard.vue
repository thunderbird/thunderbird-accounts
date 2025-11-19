<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';
import { PhXCircle } from '@phosphor-icons/vue';

const { t } = useI18n();

defineProps<{
  text: string;
  subtitle?: string;
  currentStep: number;
  totalSteps: number;
  showBack?: boolean;
  nextLabel?: string;
}>();

const emit = defineEmits(['next', 'back']);
</script>

<template>
  <div class="tour-card">
    <header>
      <p>{{ t('views.mail.ftue.step', { step: currentStep, total: totalSteps }) }}</p>
      <button class="close-button">
        <ph-x-circle size="24" />
      </button>
    </header>

    <p>{{ text }}</p>
    <p v-if="subtitle">{{ subtitle }}</p>

    <div class="buttons-container">
      <link-button v-if="showBack" size="small" @click="emit('back')">
        {{ t('views.mail.ftue.back') }}
      </link-button>

      <primary-button size="small" @click="emit('next')">
        {{ nextLabel || t('views.mail.ftue.next') }}
      </primary-button>
    </div>
  </div>
</template>

<style scoped>
/* Overriding the link button font size */
:deep(.base.link.small.filled > span) {
  font-size: 0.75rem;
}

.tour-card {
  position: absolute;
  top: 2rem;
  right: 9rem;
  transform: translateX(50%);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 240px;
  padding: 0.75rem 1rem;
  color: var(--colour-ti-base);
  background-color: var(--colour-neutral-base);
  box-shadow: 0.25rem 0.25rem 1rem 0 rgba(0, 0, 0, 0.1);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  z-index: 2;

  h2 {
    font-weight: 700;
    font-size: 0.875rem;
    margin: 0;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    p {
      font-size: 0.6875rem;
    }

    .close-button {
      background: none;
      border: none;
      cursor: pointer;
      padding: 0;
      color: var(--colour-ti-muted);
    }
  }

  .buttons-container {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
}

@media (min-width: 1300px) {
  .tour-card {
    right: 0;
  }
}
</style>

