<script setup>
import MessageBar from '@/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@/svg/thunderbird-pro-light.svg';

const clientUrl = window._page.currentView?.clientUrl;

console.error('Route not implemented', {
  pageId: window?._page?.pageId,
  page: window?._page,
});
// Unhide the unformatted template
window.document.documentElement.classList.remove('route-found');
</script>

<script>
export default {
  name: 'RouteNotImplementedView'
};
</script>

<template>
  <message-bar />

  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>

  <h1>{{ $t('routeNotImplementedTitle') }}</h1>
  <p>{{ $t('routeNotImplementedText1') }}</p>
  <p>{{ $t('routeNotImplementedText2') }}</p>
</template>

<style scoped>
.notice-bar {
  position: absolute;
  top: 1rem;
  left: 1.5rem;
  right: 1.5rem;
  z-index: 1;
}

h1 {
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
  }
}
</style>