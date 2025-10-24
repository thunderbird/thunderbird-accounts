<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { BrandButton } from '@thunderbirdops/services-ui';
import UserMenu from '@/components/UserMenu.vue';

const { t } = useI18n();

const isAuthenticated = ref(window._page?.isAuthenticated);
const avatarUsername = ref(window._page?.userDisplayName || window._page?.userEmail);

const navItemsAccounts = [
  {
    route: '/dashboard',
    i18nKey: 'dashboard',
  },
  {
    route: '/manage-mfa',
    i18nKey: 'manageMfa',
  },
  {
    route: '/privacy-and-data',
    i18nKey: 'privacyAndData',
  },
];

const navItemsMail = [
  {
    route: '/mail#dashboard',
    i18nKey: 'dashboard',
  },
  {
    route: '/mail#email-settings',
    i18nKey: 'manageEmails',
  },
  {
    route: '/mail#custom-domains',
    i18nKey: 'customDomains',
  },
  {
    route: '/mail/security-settings',
    i18nKey: 'securitySettings',
  },
];

const currentRoute = useRoute();

const isThundermail = computed(() => currentRoute.path.startsWith('/mail'));
const navItems = computed(() => isThundermail.value ? navItemsMail : navItemsAccounts);

// https://vite.dev/guide/assets.html#new-url-url-import-meta-url
const logoSrc = computed(() => {
  if (isThundermail.value) {
    return new URL('../assets/svg/thundermail-logo.svg', import.meta.url).href;
  }

  return new URL('../assets/svg/thunderbird-pro-dark.svg', import.meta.url).href;
})
</script>

<template>
  <header>
    <template v-if="isThundermail">
      <router-link to="/mail">
        <img :src="logoSrc" alt="Thundermail" />
      </router-link>
    </template>
    <template v-else>
      <router-link to="/">
        <img :src="logoSrc" alt="Thunderbird Pro" />
      </router-link>
    </template>

    <template v-if="isAuthenticated">
      <nav class="desktop">
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

  nav.desktop {
    display: none;
  }

  .login-button-link {
    text-decoration: none;

    .brand.outline {
      color: #eeeef0; /* var(--colour-ti-base) dark mode */
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
    }
  }
}

@media (min-width: 1024px) {
  header {
    padding: 1rem 3.5rem;
  }
}
</style>