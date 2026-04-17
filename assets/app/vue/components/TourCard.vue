<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { LinkButton, PrimaryButton } from '@thunderbirdops/services-ui';
import { PhXCircle } from '@phosphor-icons/vue';

const { t } = useI18n();

const props = withDefaults(defineProps<{
  text: string;
  title?: string;
  subtitle?: string;
  currentStep: number;
  totalSteps: number;
  showBack?: boolean;
  nextLabel?: string;
  variant?: 'section' | 'header' | 'welcome';
}>(), {
  variant: 'section',
});

const emit = defineEmits(['next', 'back', 'close']);

const isWelcome = computed(() => props.variant === 'welcome');
</script>

<template>
  <div
    class="tour-card"
    :class="{
      'tour-card--header': variant === 'header' || variant === 'welcome',
    }"
    role="dialog"
    :aria-label="isWelcome ? title : t('views.mail.ftue.step', { step: currentStep, total: totalSteps })"
    aria-modal="false"
    tabindex="-1"
  >
    <header v-if="!isWelcome">
      <p>{{ t('views.mail.ftue.step', { step: currentStep, total: totalSteps }) }}</p>
      <button class="close-button" :aria-label="t('views.mail.ftue.close')" @click="emit('close')">
        <ph-x-circle size="24" />
      </button>
    </header>

    <div class="content">
      <h2 v-if="isWelcome && title">{{ title }}</h2>
      <p>{{ text }}</p>
      <p v-if="subtitle">{{ subtitle }}</p>
  
      <div class="buttons-container">
        <link-button v-if="isWelcome" size="small" @click="emit('close')">
          {{ t('views.mail.ftue.skip') }}
        </link-button>
        <link-button v-else-if="showBack" size="small" @click="emit('back')">
          {{ t('views.mail.ftue.back') }}
        </link-button>
  
        <primary-button size="small" @click="emit('next')">
          {{ nextLabel || t('views.mail.ftue.next') }}
        </primary-button>
      </div>
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
  gap: 0.5rem;
  width: 240px;
  padding: 0.75rem 1rem;
  color: var(--colour-ti-base);
  background-color: var(--colour-neutral-base);
  box-shadow: 0 0.5rem 1rem 0 rgba(0, 0, 0, 0.2);
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
      height: 1.5rem;
      background: none;
      border: none;
      cursor: pointer;
      padding: 0;
      color: var(--colour-ti-muted);
    }
  }

  .content {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .buttons-container {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
}

.tour-card--header {
  top: 4.75rem;
  right: 2rem;
  z-index: 10;
  transform: none;
}

@media (min-width: 1280px) {
  .tour-card {
    top: -0.625rem;
    right: 0;
  }

  .tour-card--header {
    top: 4.75rem;
    right: 2rem;
  }
}
</style>

