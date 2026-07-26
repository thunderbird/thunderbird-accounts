<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import FooterBar from '@/components/FooterBar.vue';
import { STATUS_PAGE_URL } from '@/defines';
import { computed } from 'vue';
import { useRouter } from 'vue-router';

const isAuthenticated = window._page?.isAuthenticated;

const router = useRouter();
const { t } = useI18n();
const props = defineProps<{
  is404: boolean;
  isRateLimit: boolean;
}>();

const errorTitle = computed(() => {
  if (props?.is404) {
    return t('views.error.notFoundError');
  } else if (props?.isRateLimit) {
    return t('views.error.rateLimitError');
  }
  return (window._page.errorTitle ?? t('views.error.fallbackError'))
});
const errorMessage = computed(() => {
  if (props?.is404) {
    return isAuthenticated ? 'views.error.notFoundMessage.textAuth' : 'views.error.notFoundMessage.textNoAuth';
  }
  else if (props?.isRateLimit) {
    return 'views.error.rateLimitMessage.text';
  }
  return 'views.error.serverErrorMessage.text';
});
const errorLink = computed(() => {
  if (props?.is404) {
    return t('views.error.notFoundMessage.link');
  } else if (props?.isRateLimit) {
    return t('views.error.rateLimitMessage.link');
  }
  return t('views.error.serverErrorMessage.link');
});
const errorHref = computed(() => {
  if (props?.is404) {
    return '/';
  }

  return STATUS_PAGE_URL;
});
const errorAction = (evt) => {
  // Hit that back button!
  router.back();
}
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
        <h2>{{ errorTitle }}</h2>
        <i18n-t :keypath="errorMessage" tag="p">
          <template #link>
            <a href="#" @click.prevent="errorAction" v-if="isRateLimit">{{ errorLink }}</a>
            <a :href="errorHref" v-else>{{ errorLink }}</a>
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
