<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import MessageBar from '@kc/vue/components/MessageBar.vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import { useThrottleFn } from '@vueuse/core';

const route = useRoute();
const { t } = useI18n();
const form = useTemplateRef<HTMLFormElement>("form");

defineProps<{
  title: string;
  subtitle: string;
  submitDisabled: boolean | null;
  submitTitle: string;
}>();

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
  <header>
    <h1 aria-live="polite" class="title" data-testid="title">{{ title }}</h1>
    <p  aria-live="polite" class="text" data-testid="subtitle">{{ subtitle }}</p>
    <slot name="notice-bars"/>
  </header>

  <main>
    <form @submit.prevent="onSubmit()" @keyup.enter="onSubmit()" ref="form">
        <div class="form-elements">
          <slot name="form-elements" />
          <slot name="form-extras" />
        </div>
        <div class="buttons">
          <primary-button form-action="submit" data-testid="submit-button" class="submit" :disabled="submitDisabled"
            @click="onSubmit()">
            {{ $t('views.mail.views.signUp.continue') }}
          </primary-button>
        </div>
      </form>
  </main>
</template>

<style scoped>
#i18n-workaround {
  display: none;
}

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

.logo-link {
  display: block;
  text-decoration: none;
  margin-block-end: 2.8125rem;

  .logo {
    height: 36px;
    width: auto;
    transition: opacity 0.2s ease;

    &:hover {
      opacity: 0.8;
    }
  }
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
