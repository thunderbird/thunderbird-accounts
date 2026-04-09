<script setup lang="ts">
import { ref } from 'vue';
import ThundermailLogo from '@kc/svg/thundermail-logo-blue.svg';

// Featured image imports / dpi variants
import featuredImagePng from '@kc/images/featured-image/left-graphic.png';
import featuredImageWebp from '@kc/images/featured-image/left-graphic.webp';
import featuredImageAvif from '@kc/images/featured-image/left-graphic.avif';

import featuredImagePng2x from '@kc/images/featured-image/left-graphic@2x.png';
import featuredImageWebp2x from '@kc/images/featured-image/left-graphic@2x.webp';
import featuredImageAvif2x from '@kc/images/featured-image/left-graphic@2x.avif';

import featuredImagePng3x from '@kc/images/featured-image/left-graphic@3x.png';
import featuredImageWebp3x from '@kc/images/featured-image/left-graphic@3x.webp';
import featuredImageAvif3x from '@kc/images/featured-image/left-graphic@3x.avif';

const clientUrl = window._page.currentView?.clientUrl;

</script>

<template>
  <section class="bolt-defaults">
    <div class="card">
      <!-- Left side: Featured image -->
      <div class="left-side">
        <picture>
          <source :srcset="`${featuredImageAvif}, ${featuredImageAvif2x} 2.0x, ${featuredImageAvif3x} 3.0x`"
            type="image/avif" />
          <source :srcset="`${featuredImageWebp}, ${featuredImageWebp2x} 2.0x, ${featuredImageWebp3x} 3.0x`"
            type="image/webp" />
          <source :srcset="`${featuredImagePng}, ${featuredImagePng2x} 2.0x, ${featuredImagePng3x} 3.0x`"
            type="image/png" />
          <img class="featured-image" :src="featuredImagePng" alt="" />
        </picture>
      </div>

      <!-- Right side: Panel -->
      <div class="right-side">
        <div class="panel">
          <a :href="clientUrl" class="logo-link">
            <img :src="ThundermailLogo" alt="Thundermail" class="base-template__logo" />
          </a>
          <slot />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
section {
  /* A little over 52rem to avoid some overlap. Ideally this should align with the featured image's height. */
  --max-card-height: 52.1rem;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;

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
      max-height: auto;

      .left-side {
        display: block;
        flex: 1;
        max-width: 556px;
        min-height: 100vh;
        background-color: var(--colour-ti-base);

        .featured-image {
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

        .featured-image {
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
