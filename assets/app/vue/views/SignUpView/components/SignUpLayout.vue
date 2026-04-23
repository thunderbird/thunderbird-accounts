<script setup lang="ts">
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import { useThrottleFn } from '@vueuse/core';

const form = useTemplateRef<HTMLFormElement>("form");

withDefaults(defineProps<{
  stepId: string;
  title: string;
  subtitle: string;
  submitDisabled?: boolean;
  submitTitle?: string;
  hideActions?: boolean;
}>(), {
  submitDisabled: false,
  hideActions: false
});

const emit = defineEmits<{
  (e: 'submit'): void;
}>();

// Throttle to prevent emitting a bunch of events at once
const onSubmit = useThrottleFn(() => {
  if (!form?.value.checkValidity()) {
    return;
  }
  emit('submit');
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
        <primary-button form-action="submit" data-testid="submit-button" class="submit" :disabled="submitDisabled"
          @click.prevent="onSubmit()">
          {{ submitTitle || $t('views.mail.views.signUp.continue') }}
        </primary-button>
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
  }

}

.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;

  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}
</style>
