<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { WAFFLE_FLAG } from '@/types';
import { isWaffleFlagActive } from '@/utils';
import { BrandButton } from '@thunderbirdops/services-ui';
import UserMenu from '@/components/UserMenu.vue';

const { t } = useI18n();

const isAuthenticated = ref(window._page?.isAuthenticated);
const avatarUsername = ref(window._page?.userDisplayName || window._page?.userEmail);

const navItems = [
  {
    route: '/mail',
    i18nKey: 'dashboard',
  },
  {
    route: '/custom-domains',
    i18nKey: 'customDomains',
  },
];

const currentRoute = useRoute();

const needsTosAcceptance = ref(window._page?.needsTosAcceptance);
const needsSubscription = ref(
  window._page?.isAwaitingPaymentVerification || !window._page?.hasActiveSubscription,
);
const isCustomDomainsRevampActive = computed(() => isWaffleFlagActive(WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP));
const showNav = computed(() => !needsTosAcceptance.value && !needsSubscription.value && isCustomDomainsRevampActive.value);

// https://vite.dev/guide/assets.html#new-url-url-import-meta-url
const logoSrc = new URL('@/assets/svg/thundermail-logo.svg', import.meta.url).href;
</script>

<template>
  <header>
    <router-link to="/mail">
      <img :src="logoSrc" alt="Thundermail" />
    </router-link>

    <template v-if="isAuthenticated">
      <nav v-if="showNav" class="desktop">
        <ul>
          <li v-for="navItem in navItems" :key="navItem.route">
            <router-link :to="navItem.route" :class="{ active: currentRoute.path === navItem.route }">
              {{ t(`navigationLinks.${navItem.i18nKey}`) }}
            </router-link>
          </li>
        </ul>
      </nav>

      <user-menu :username="avatarUsername" />
    </template>

    <template v-else>
      <!-- Login is done through Django routing and not Vue router -->
      <a href="/login/" class="login-button-link">
        <brand-button variant="outline">
          {{ t('navigationLinks.login') }}
        </brand-button>
      </a>
    </template>
  </header>
</template>

<style scoped>
header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  height: 68px;
  padding: 1rem;
  backdrop-filter: blur(24px);
  box-shadow: 0 0.5rem 1.5rem 0 rgba(0, 0, 0, 0.1);
  background-image: linear-gradient(to top, #1a202c, #2f3a50);
  width: 100%;

  /* Without this we can't be on top of main content when we need */
  position: relative;
  z-index: var(--z-index-header-dropdown);

  &:first-child {
    margin-right: auto;
  }

  &:last-child {
    margin-left: auto;
  }

  nav.desktop {
    display: none;
  }

  .login-button-link {
    text-decoration: none;

    .brand.outline {
      color: #eeeef0;
      /* var(--colour-ti-base) dark mode */
    }
  }

  ul {
    display: flex;
    gap: 0.5rem;
    font-family: metropolis;
    font-weight: 600;
    font-size: 0.8125rem;
    letter-spacing: 0.65px;
    text-transform: uppercase;

    a {
      color: white;
      text-decoration: none;
      padding: 0.75rem 1.25rem;

      &.active {
        background-color: #18181b;
        border-radius: 0.5rem;
        box-shadow: inset 0 0.25rem 0.25rem 0 rgba(0, 0, 0, 0.15);
      }
    }
  }
}

@media (min-width: 768px) {
  header {
    nav.desktop {
      display: block;
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
    }
  }
}

@media (min-width: 1024px) {

  header> :first-child,
  header> :last-child {
    padding: 1rem 3.5rem;
  }

}
</style>
