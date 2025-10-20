<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { StandardFooter } from '@thunderbirdops/services-ui';

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
</script>

<template>
  <standard-footer contributeToThisSiteUrl="https://github.com/thunderbird/thunderbird-accounts">
    <template #default>
      <nav>
        <router-link to="/">
          <img src="@/assets/svg/thunderbird-pro-dark.svg" alt="Thunderbird Pro Logo" />
        </router-link>
        <ul>
          <li v-for="navItem in navItems" :key="navItem.route">
            <router-link :to="navItem.route">
              {{ t(`navigationLinks.${navItem.i18nKey}`) }}
            </router-link>
          </li>
        </ul>
      </nav>
    </template>

    <template #privacyPolicy>
      <router-link to="/privacy">
        {{ t('footer.privacyPolicy') }}
      </router-link>
    </template>

    <template #legal>
      <router-link to="/terms">
        {{ t('footer.legal') }}
      </router-link>
    </template>
  </standard-footer>
</template>

<style scoped>
nav {
  display: flex;
  flex-direction: column;
  align-items: start;
  justify-content: space-between;

  img {
    align-self: start;
    margin-block-end: 2rem;
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
}

@media (min-width: 768px) {
  nav {
    flex-direction: row;
    align-items: center;

    img {
      margin-block-end: 0;
    }

    ul {
      gap: 3rem;
    }
  }
}
</style>