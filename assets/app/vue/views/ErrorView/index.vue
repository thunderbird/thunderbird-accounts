<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import FooterBar from '@/components/FooterBar.vue';
import { STATUS_PAGE_URL } from '@/defines';
import { computed } from 'vue';

const isAuthenticated = window._page?.isAuthenticated;

const { t } = useI18n();
const props = defineProps<{
  is404: boolean;
}>();

const error_title = computed(() => props?.is404 ? t('views.error.notFoundError') : (window._page.errorTitle ?? t('views.error.fallbackError')));
const error_message = computed(() => {
  if (props?.is404) {
    return isAuthenticated ? 'views.error.notFoundMessage.textAuth' : 'views.error.notFoundMessage.textNoAuth';
  }
  return 'views.error.message.serverErrorText';
});
const error_link = computed(() => props?.is404 ? t('views.error.notFoundMessage.link') : t('views.error.serverErrorMessage.link'));
const error_href = computed(() => props?.is404 ? '/' : STATUS_PAGE_URL);
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
        <i18n-t :keypath="error_message" tag="p">
          <template #link>
            <a :href="error_href">{{ error_link }}</a>
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