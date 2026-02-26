<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import FooterBar from '@/components/FooterBar.vue';
import { STATUS_PAGE_URL } from '@/defines';

const { t } = useI18n();

const error_title = window._page.errorTitle ?? t('views.error.fallbackError');
</script>

<script lang="ts">
export default {
  name: 'ErrorView',
};
</script>

<template>
  <div class="page-container">
    <main>
      <div class="error-view">
        <h2>{{ error_title }}</h2>
        <i18n-t keypath="views.error.message.text" tag="p">
          <template #link>
            <a :href="STATUS_PAGE_URL">{{ t('views.error.message.link') }}</a>
          </template>
        </i18n-t>
      </div>
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

.server-messages {
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  .server-message {
    max-width: 60rem;
    margin: 1rem;
  }
}

@media (min-width: 1024px) {
  main {
    margin: 0 auto;
    padding: 3rem 3.5rem;
  }
}
</style>