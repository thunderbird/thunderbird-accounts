<script setup>
import { computed, ref } from "vue";
import router from "../router";

  console.log("And attached!!");

  console.log('page id', window._page.pageId);

  // Work-around for pages that don't have unique routes
  const pageId = ref(window._page.pageId);
  if (pageId.value === 'login-page-expired') {
    router.replace({ name: 'page-expired' });
  }


</script>

<template>
  <section class="centre-panel">
    {{pageId}}
    <router-view/>
  </section>

</template>

<style scoped>
.centre-panel {
  height: 100%;
  max-width: 37.5rem;
  margin: auto;

  border-radius: 0.5rem;
  border: 0.0625rem solid #6a6e76;
}
</style>