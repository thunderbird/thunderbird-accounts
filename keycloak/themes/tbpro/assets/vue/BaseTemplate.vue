<script setup lang="ts">
import { ref } from 'vue';
import ThundermailLogo from '@kc/svg/thundermail-logo-blue.svg';

const clientUrl = window._page.currentView?.clientUrl;

</script>

<template>
  <section class="bolt-defaults">
    <div class="card">
      <!-- Left side: Featured image -->
      <div class="left-side"></div>

      <!-- Right side: Panel -->
      <div class="right-side">
        <div class="panel">
          <a :href="clientUrl" class="logo-link">
            <img :src="ThundermailLogo" alt="Thundermail" class="base-template__logo" />
          </a>
          <div class="panel-contents">
            <slot />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
section {
  /* A little over 52rem to avoid some overlap. Ideally this should align with the featured image's height. */
  /*--max-card-height: 52.1rem;*/
  --max-card-height: 45rem;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;

  .left-side {
    /* Fallback support */
    background-image: url("@kc/images/featured-image/left-graphic.png");
    /* Handle the resolution and image type picks for supported devices. */
    background-image: image-set(url("@kc/images/featured-image/left-graphic.avif") 1x type("image/avif"),
        url("@kc/images/featured-image/left-graphic@2x.avif") 2x type("image/avif"),
        url("@kc/images/featured-image/left-graphic@3x.avif") 3x type("image/avif"),

        url("@kc/images/featured-image/left-graphic.webp") 1x type("image/webp"),
        url("@kc/images/featured-image/left-graphic@2x.webp") 2x type("image/webp"),
        url("@kc/images/featured-image/left-graphic@3x.webp") 3x type("image/webp"),

        url("@kc/images/featured-image/left-graphic.png") 1x type("image/png"),
        url("@kc/images/featured-image/left-graphic@2x.png") 2x type("image/png"),
        url("@kc/images/featured-image/left-graphic@3x.png") 3x type("image/png"),
      );
    background-repeat: no-repeat;
    background-size: cover;
    background-position: center;
  }

  .base-template__logo {
    height: 3rem;
  }

  .card {
    width: 100%;
    height: auto;
    min-height: 100vh;
    max-height: var(--max-card-height);
    display: flex;
    align-items: stretch;
    justify-content: center;
    background-color: inherit;

    .left-side {
      display: none;
      position: relative;
    }

    .right-side {
      position: relative;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      flex: 1;
      background-color: var(--colour-neutral-base, #ffffff);
    }

    .panel {
      height: 100%;
      display: flex;
      flex-direction: column;
      gap: 3rem;
      padding: 6rem 2rem;

      &:has(.notice-bar) {
        padding: 6rem 2rem;
      }
    }
  }
}

@media (min-width: 640px) {
  section {
    .card {
      max-height: auto;

      .left-side {
        display: block;
        flex: 1;
        max-width: 556px;
        min-height: 100vh;
        background-color: var(--colour-ti-base);
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
      --card-border-radius: 2rem;
      width: 1280px;
      height: auto;
      min-height: 720px;
      border-radius: var(--card-border-radius);
      align-items: initial;
      border: 0.0625rem solid var(--colour-neutral-border-intense);

      .left-side {
        background-color: unset;
        height: auto;
        min-height: auto;
        border-radius: var(--card-border-radius);
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

        .panel-contents {
          display: flex;
          flex-direction: column;
          justify-content: center;
        }
      }
    }
  }
}
</style>
