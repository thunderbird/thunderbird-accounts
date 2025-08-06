<script setup>
console.error('Route not implemented', {
  pageId: window?._page?.pageId,
  page: window?._page,
})
// Unhide the unformatted template
window.document.documentElement.classList.remove('route-found');
</script>

<script>
export default {
  name: 'RouteNotImplementedView'
}
</script>

<template>
  <div class="panel">
    <h1>Route Not Implemented</h1>
    <p>This route isn't implemented, please report this issue and the route name in the top left corner.</p>
    <p>You can use the unformatted template below this panel to continue.</p>
  </div>
</template>

<style scoped>
.panel {
  margin: 30px
}
</style>
