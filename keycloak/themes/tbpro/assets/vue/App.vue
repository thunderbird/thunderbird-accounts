<script setup>
import { ref } from "vue";
import router from "../router";

// Match routes based on pageId / route name
const pageId = ref(window._page.pageId);
const routeName = pageId.value && router.hasRoute(pageId.value) ? pageId.value : 'route-not-implemented';
console.log('route:', routeName);
router.replace({name: routeName});


const playingAnimation = ref(false);
const onWiggle = async () => {
  playingAnimation.value = true;
  window.setTimeout(() => {
    playingAnimation.value = false;
  }, 1000);
};

</script>

<template>
  <section>
    <div class="debug-page-id" @click="onWiggle" :class="{wiggle: playingAnimation}">{{ pageId }}</div>
    <router-view/>
  </section>
</template>

<style scoped>
section {
  height: 100%;
}

.wiggle {
  animation: wiggle 1s
}

.debug-page-id {
  cursor: pointer;
  position: absolute;
  top: 1rem;
  left: 1rem;
  background-color: black;
  color: white;
  border-radius: 1rem;
  padding: 0.5rem;
}

:deep(.panel) {
  margin: 30px
}
</style>
