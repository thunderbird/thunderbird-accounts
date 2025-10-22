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
  background-color: var(--colour-neutral-lower);
}

main {
  flex: 1 1 auto;
  padding: 3rem 1rem;
  width: 100%;
  max-width: 1280px;
}

@media (min-width: 1024px) {
  main {
    margin: 0 auto;
    padding: 3rem 3.5rem;
  }
}
</style>
