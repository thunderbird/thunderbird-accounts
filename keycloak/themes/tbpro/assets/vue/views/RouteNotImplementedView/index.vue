<script setup>
import MessageBar from '@/vue/components/MessageBar.vue';

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
  <div class="panel">
    <h1>{{ $t('routeNotImplementedTitle') }}</h1>
    <message-bar />
    <p>{{ $t('routeNotImplementedText1') }}</p>
    <p>{{ $t('routeNotImplementedText2') }}</p>
  </div>
</template>
