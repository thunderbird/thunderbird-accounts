<script setup lang="ts">
import HeaderBar from '@/components/HeaderBar.vue';
import FooterBar from '@/components/FooterBar.vue';
</script>

<template>
  <div class="page-container">
    <header-bar />

    <main>
      <router-view />
    </main>

    <footer-bar />
  </div>
</template>

<style scoped>
.page-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

main {
  flex: 1 1 auto;
  max-width: 782px;
  margin: 0 auto;
  padding: 3rem 0;
}
</style>