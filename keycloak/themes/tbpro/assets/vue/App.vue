<script setup lang="ts">
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
        <div class="panel">
          <router-view />
        </div>
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
  z-index: 2;
}

section {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;

  .card {
    width: 100%;
    height: auto;
    min-height: 100vh;
    display: flex;
    align-items: stretch;
    justify-content: center;
    background-color: inherit;

    .left-side {
      display: none;
    }

    .right-side {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 100vh;
      flex: 1;
      background-color: var(--colour-neutral-base, #ffffff);
    }

    .panel {
      padding: 0 2rem;

      &:has(.notice-bar) {
        padding: 6rem 2rem;
      }
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
        min-height: 100vh;
        background-color: var(--colour-ti-base);

        .orb-graphic {
          display: block;
          width: 100%;
          height: 100%;
          min-height: 100vh;
          object-fit: cover;
        }
      }
    }
  }
}

@media (min-width: 1280px) {
  section {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background-color: var(--colour-ti-base);
    padding: 1rem;

    .card {
      width: 1280px;
      height: auto;
      min-height: 720px;
      border-radius: 2rem;
      align-items: initial;
      border: 0.0625rem solid var(--colour-neutral-border-intense);

      .left-side {
        background-color: unset;
        height: auto;
        min-height: auto;

        .orb-graphic {
          min-height: auto;
          border-radius: 2rem 0 0 2rem;
        }
      }

      .right-side {
        border-radius: 0 2rem 2rem 0;
        min-height: auto;

        .panel {
          padding: 6rem 10rem 5.625rem 6rem;

          &:has(.notice-bar) {
            padding: 6rem 10rem 5.625rem 6rem;
          }
        }
      }
    }
  }
}
</style>
