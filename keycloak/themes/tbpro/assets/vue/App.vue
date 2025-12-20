<script setup lang="ts">
import { ref } from 'vue';
import router from '../router';
import BaseTemplate from '@kc/vue/BaseTemplate.vue';

// Match routes based on pageId / route name
const pageId = ref(window._page.pageId);
const routeName = pageId.value && router.hasRoute(pageId.value) ? pageId.value : 'route-not-implemented';
console.log('route:', routeName);
router.replace({ name: routeName });
</script>

<template>
  <base-template>
    <router-view />
  </base-template>
</template>
