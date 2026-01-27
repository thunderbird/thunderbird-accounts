<script setup lang="ts">
import { onMounted, ref } from 'vue';
import router from '../router';
import BaseTemplate from '@kc/vue/BaseTemplate.vue';

// Match routes based on pageId / route name
const pageId = ref(window._page.pageId);
const routeName = pageId.value && router.hasRoute(pageId.value) ? pageId.value : 'route-not-implemented';
// Information for easier debugging
console.info({
  route: routeName,
  pageId: pageId.value,
});
router.replace({ name: routeName });

onMounted(() => {
  window.document.body.dataset['testid'] = 'vue-app';
});
</script>

<template>
  <base-template>
    <router-view />
  </base-template>
</template>
