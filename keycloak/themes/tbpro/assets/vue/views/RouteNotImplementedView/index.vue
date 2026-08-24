<script setup>
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
  <h2>{{ $t('routeNotImplementedTitle') }}</h2>
  <p>{{ $t('routeNotImplementedText1') }}</p>
  <p>{{ $t('routeNotImplementedText2') }}</p>
</template>
