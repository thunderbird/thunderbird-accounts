<script setup>
import MessageBar from '@kc/vue/components/MessageBar.vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { computed, onMounted } from 'vue';

const message = window._page.message;
const messageHeader = window._page.currentView?.messageHeader;
const actionUrl = window._page.currentView?.actionUrl;
const actionText = window._page.currentView?.actionText;
const requiredActions = window._page.currentView?.requiredActions ?? {};

const isSingleAction = computed(() => Object.keys(requiredActions).length === 1);
const isVerifyEmailAction = computed(() => isSingleAction.value && Object.keys(requiredActions)[0] === 'VERIFY_EMAIL');
</script>

<script>
export default {
  name: 'InfoView'
};
</script>

<template>
  <header>
    <h1 class="title">
      <template v-if="isVerifyEmailAction">
        {{ $t('infoVerifyEmailTitle') }}
      </template>
      <template v-else-if="messageHeader">
        {{ messageHeader }}
      </template>
      <template v-else>
        {{ message?.summary }}
      </template>
    </h1>
    <p class="text" v-if="isVerifyEmailAction">{{ $t('infoVerifyEmailText') }}</p>
    <message-bar v-if="messageHeader && messageHeader !== message?.summary" />
  </header>
  <main>
    <ul class="required-actions" v-if="!isSingleAction">
      <li v-for="action in requiredActions" v-bind:key="action">{{ action }}</li>
    </ul>
    <template v-if="actionUrl">
      <primary-button class="perform-action" :href="actionUrl" data-testid="action-url">{{ actionText
        }}</primary-button>
    </template>
  </main>
</template>

<style scoped>
.notice-bar {
  position: absolute;
  top: 1rem;
  left: 1.5rem;
  right: 1.5rem;
  z-index: 1;
}

.required-actions {
  margin: 0;
  margin-bottom: 1.5rem;

  li {
    list-style: none;
  }
}

header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 0 0 3rem 0;

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

  .title,
  .text {
    margin: 0;
  }
}

main {
  display: flex;
  flex-direction: column;
}

.perform-action {
  align-self: flex-end;
  width: fit-content;
}
</style>
