<script setup lang="ts">
import { UserAvatar } from '@thunderbirdops/services-ui';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

const { t } = useI18n();

const navItems = [
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

const currentRoute = useRoute();
</script>

<template>
  <header>
    <router-link to="/">
      <img src="@/assets/svg/thunderbird-pro-dark.svg" alt="Thunderbird Pro Logo" />
    </router-link>

    <nav class="desktop">
      <ul>
        <li v-for="navItem in navItems" :key="navItem.route">
          <router-link :to="navItem.route" :class="{ active: currentRoute.path === navItem.route }">
            {{ t(`navigationLinks.${navItem.i18nKey}`) }}
          </router-link>
        </li>
      </ul>
    </nav>

    <!-- TODO: Update with actual user data & add dropdown -->
    <user-avatar username="test" />
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