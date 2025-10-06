<script setup>
import { ref } from "vue";
import OrbGraphic from '@/images/orb-graphic.png';
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

    <div class="card">
      <!-- Left side: Orb graphic -->
      <div class="left-side">
        <img :src="OrbGraphic" alt="Thunderbird Orb" class="orb-graphic" />
      </div>

      <!-- Right side: Panel -->
      <div class="right-side">
        <router-view />
      </div>
    </div>
  </section>
</template>

<style scoped>
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

section {
  height: 100%;

  .card {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: inherit;

    .left-side {
      display: none;
    }

    .right-side {
      position: relative;
      display: flex;
      flex-direction: column;
      background-color: var(--colour-neutral-base, #ffffff);
    }
  }
}

@media (min-width: 640px) {
  section {
    .card {
      .left-side {
        display: block;
        flex: 1;
        max-width: 556px;
        height: 100%;

        .orb-graphic {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: contain;
        }
      }

      .right-side {
        flex: 1;
      }
    }
  }
}

@media (min-width: 1280px) {
  section {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    background-color: var(--colour-ti-base);

    .card {
      max-width: 1280px;
      max-height: 720px;
      border-radius: 2rem;
      align-items: initial;
      border: 0.0625rem solid var(--colour-neutral-border-intense);

      .right-side {
        border-radius: 0 2rem 2rem 0;
      }
    }
  }
}
</style>
