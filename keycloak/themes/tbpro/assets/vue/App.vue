<script setup>
import { computed, ref } from "vue";
import router from "../router";

// Match routes based on pageId / route name
const pageId = ref(window._page.pageId);
const routeName = pageId.value && router.hasRoute(pageId.value) ? pageId.value : 'route-not-implemented';
console.log('route:', routeName);
router.replace({name: routeName});

</script>

<template>
  <section class="centre-panel">
    <div class="debug-page-id">{{ pageId }}</div>
    <router-view/>
  </section>

</template>

<style scoped>
.debug-page-id {
  position: absolute;
  top: 1rem;
  left: 1rem;
  background-color: black;
  color: white;
  border-radius: 1rem;
  padding: 0.5rem;
}

.centre-panel {
  height: 100%;
  max-width: 37.5rem;
  margin: auto;

  border-radius: 0.5rem;
  border: 0.0625rem solid #6a6e76;
}
</style>