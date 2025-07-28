<script setup lang="ts">
  console.log("And attached!!");
</script>

<template>
  <section class="centre-panel">
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