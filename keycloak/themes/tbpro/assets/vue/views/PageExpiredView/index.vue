<script setup>
import MessageBar from '@/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@/svg/thunderbird-pro-light.svg';

const restartFlowUrl = window._page.currentView?.restartFlowUrl;
const loginUrl = window._page.currentView?.loginUrl;
const clientUrl = window._page.currentView?.clientUrl;
</script>

<script>
export default {
  name: 'PageExpiredView'
};
</script>

<template>
  <message-bar/>

  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>

  <h2>{{ $t('pageExpiredTitle') }}</h2>
  <div class="buttons">
    <p>{{ $t('pageExpiredMsg1') }} <a data-testid="restart-flow-url" :href="restartFlowUrl">{{ $t('doClickHere') }}</a></p>
    <p>{{ $t('pageExpiredMsg2') }} <a data-testid="login-url" :href="loginUrl">{{ $t('doClickHere') }}</a></p>
  </div>
</template>

<style scoped>
.notice-bar {
  position: absolute;
  top: 1rem;
  left: 1.5rem;
  right: 1.5rem;
  z-index: 1;
}

h2 {
  font-size: 1.5rem;
  font-family: metropolis;
  font-weight: normal;
  line-height: 1.1;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
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

.buttons {
  margin-top: var(--space-24);
  width: 100%;
}
</style>
