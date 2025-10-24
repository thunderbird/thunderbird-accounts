<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { StandardFooter } from '@thunderbirdops/services-ui';

const { t } = useI18n();

const isAuthenticated = ref(window._page?.isAuthenticated);

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
    route: '/mail',
    i18nKey: 'dashboard',
  },
  {
    route: '/mail#manage-emails',
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
    return new URL('@/assets/svg/thundermail-logo.svg', import.meta.url).href;
  }

  return new URL('@/assets/svg/thunderbird-pro-dark.svg', import.meta.url).href;
})
</script>

<template>
  <standard-footer contributeToThisSiteUrl="https://github.com/thunderbird/thunderbird-accounts">
    <template #default>
      <nav>
        <router-link to="/">
          <img :src="logoSrc" :alt="isThundermail ? 'Thundermail' : 'Thunderbird Pro'" />
        </router-link>
        <ul>
          <template v-if="isAuthenticated">
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