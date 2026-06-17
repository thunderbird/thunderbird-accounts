<script setup lang="ts">
import { BrandButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import { useThrottleFn } from '@vueuse/core';
import { PhArrowRight } from '@phosphor-icons/vue';

const form = useTemplateRef<HTMLFormElement>("form");

withDefaults(defineProps<{
  stepId: string;
  title: string;
  subtitle: string;
  submitDisabled?: boolean;
  submitTitle?: string;
  alternativeActionTitle?: string;
  showAlternativeAction?: boolean;
  hideActions?: boolean;
}>(), {
  submitDisabled: false,
  hideActions: false,
  showAlternativeAction: false
});

const emit = defineEmits<{
  (e: 'submit'): void;
  (e: 'alternativeAction'): void;
}>();

// Throttle to prevent emitting a bunch of events at once
const onSubmit = useThrottleFn(() => {
  if (!form?.value.checkValidity()) {
    return;
  }
  emit('submit');
}, 1000);

const onAlternativeAction = useThrottleFn(() => {
  emit('alternativeAction');
}, 1000);
</script>

<script lang="ts">
export default {
  name: 'SignUpLayout'
};
</script>

<template>
  <!-- Hidden element for testing purposes, don't worry about it. -->
  <input type="hidden" aria-hidden="true" data-testid="step-id" :value="stepId" />

  <header>
    <h1 aria-live="polite" class="title" data-testid="title">{{ title }}</h1>
    <p aria-live="polite" class="text" data-testid="subtitle">{{ subtitle }}</p>
    <slot name="notice-bars" />
  </header>

  <main>
    <form @submit.prevent="onSubmit()" @keyup.enter="onSubmit()" ref="form">
      <div class="form-elements">
        <slot name="form-elements" />
        <slot name="form-extras" />
      </div>
      <div class="buttons" v-if="!hideActions">
        <brand-button variant="outline" v-if="showAlternativeAction" @click.prevent="onAlternativeAction()">
          {{ alternativeActionTitle || $t('views.mail.views.signUp.back') }}
        </brand-button>
        <brand-button form-action="submit" data-testid="submit-button" class="submit" :disabled="submitDisabled"
          @click.prevent="onSubmit()">
          <template #iconRight>
            <ph-arrow-right size="20" />
          </template>
          {{ submitTitle || $t('views.mail.views.signUp.continue') }}
        </brand-button>
      </div>
    </form>
  </main>
</template>

<style scoped>
.hidden {
  display: none;
}

.notice-bar {
  position: absolute;
  top: 1rem;
  left: 1.5rem;
  right: 1.5rem;
  z-index: 1;
}

header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 0 0 1.5rem 0;

  .title {
    font-size: 2.25rem;
    font-family: metropolis;
    font-weight: normal;
    font-weight: 300;

    font-stretch: normal;

    font-style: normal;
    letter-spacing: -0.36px;
    line-height: 1.2;
    color: var(--colour-primary-default);
  }

  .text {
    font-size: 1rem;
    line-height: 1.32;
    color: #272727 /* TODO: not a variable in the Design System */
  }
}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.buttons {
  display: flex;
  align-items: center;
  justify-content: end;
  gap: 1.5rem;
  margin-top: var(--space-24);
  width: 100%;
}
</style>
