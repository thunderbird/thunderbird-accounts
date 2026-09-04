<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { StandardFooter } from '@thunderbirdops/services-ui';
import { TERMS_OF_SERVICE_URL, PRIVACY_POLICY_URL, STATUS_PAGE_URL, IDEAS_PAGE_URL } from '@/defines';

const { t } = useI18n();

const isAuthenticated = ref(window._page?.isAuthenticated);

type NavItem = { route: string; i18nKey: string };

const navItems: NavItem[] = [
  {
    route: '/dashboard',
    i18nKey: 'account',
  },
];

const currentRoute = useRoute();

const isSubscribePage = computed(() => currentRoute.path.startsWith('/subscribe'));

// https://vite.dev/guide/assets.html#new-url-url-import-meta-url
const thunderbirdLogoSrc = new URL('@/assets/svg/thunderbird-logo.svg', import.meta.url).href;
</script>

<template>
  <standard-footer contributeToThisSiteUrl="https://github.com/thunderbird/thunderbird-accounts">
    <template #default>
      <nav>
        <div class="top-row">
          <img :src="thunderbirdLogoSrc" alt="Thunderbird" />
          <ul>
            <template v-if="isAuthenticated && !isSubscribePage">
              <li v-for="navItem in navItems" :key="navItem.route">
                <router-link :to="navItem.route">
                  {{ t(`navigationLinks.${navItem.i18nKey}`) }}
                </router-link>
              </li>
            </template>
            <template v-else>
              <li>
                <!-- Login is done through Django routing and not Vue router -->
                <a href="/login/" class="login-button-link">
                  {{ t('navigationLinks.login') }}
                </a>
              </li>
            </template>
          </ul>
        </div>

        <ul class="default-links">
          <a :href="STATUS_PAGE_URL" target="_blank" rel="noopener noreferrer">
            {{ t('footer.status') }}
          </a>
          <span>|</span>
          <router-link to="/contact">
            {{ t('footer.needHelp') }}
          </router-link>
          <span>|</span>
          <a :href="IDEAS_PAGE_URL" target="_blank" rel="noopener noreferrer">
            {{ t('footer.ideas') }}
          </a>
        </ul>
      </nav>
    </template>

    <template #privacyPolicy>
      <a :href="PRIVACY_POLICY_URL" target="_blank" rel="noopener noreferrer">
        {{ t('footer.privacyPolicy') }}
      </a>
    </template>

    <template #legal>
      <a :href="TERMS_OF_SERVICE_URL" target="_blank" rel="noopener noreferrer">
        {{ t('footer.legal') }}
      </a>
    </template>
  </standard-footer>
</template>

<style scoped>
nav {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: 1.75rem;

  .top-row {
    display: flex;
    flex-direction: column;
    align-items: start;
    width: 100%;

    img {
      margin-block-end: 2rem;
    }
  }

  ul {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-family: metropolis;
    font-weight: 600;
    font-size: 0.8125rem;
    text-transform: uppercase;

    /* FIXME: This should be a var but we don't have a background
    for the footer in light mode yet so it is not readable if not white-ish */
    color: white;
  }

  .default-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    font-family: Inter;
    font-weight: 400;
    font-size: 0.6875rem;
    text-transform: none;
    color: #d4d4d8; /* TODO: This colour should be --colour-ti-secondary but it's not updated in services-ui yet */

    a {
      text-decoration: underline;
      color: inherit;
    }
  }
}

@media (min-width: 768px) {
  nav {
    gap: 0.75rem;

    .top-row {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      height: 61px;

      img {
        margin-block-end: 0;
      }
    }

    .default-links {
      width: 100%;
      justify-content: flex-end;
    }

    ul {
      gap: 3rem;
    }
  }
}
</style>
