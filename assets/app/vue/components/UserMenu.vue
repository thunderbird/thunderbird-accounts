<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useTemplateRef, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { UserAvatar } from '@thunderbirdops/services-ui';
import { getSubscriptionPortalLink } from '@/views/DashboardView/api';

defineProps<{
  username: string;
}>();

const { t } = useI18n();

const accountItem = {
  label: t('components.userMenu.myAccount'),
  to: '/dashboard',
};

const supportItem = {
  label: t('components.userMenu.support'),
  to: '/contact',
};

const manageSubscriptionLabel = computed(() => t('components.userMenu.manageSubscription'));

const openSubscriptionPortal = async () => {
  showMenu.value = false;
  try {
    const { url } = await getSubscriptionPortalLink();
    window.open(url, '_blank');
  } catch (error) {
    console.error('Unable to open the subscription portal', error);
  }
};

const externalMenuItems = [
  {
    label: t('components.userMenu.logout'),
    href: '/logout/',
  },
];

const showMenu = ref(false);
const menuRef = useTemplateRef<HTMLElement>('menuRef');

const toggleMenu = () => {
  showMenu.value = !showMenu.value;
};

const handleClickOutside = (event: MouseEvent) => {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    showMenu.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <button class="user-menu" ref="menuRef">
    <user-avatar :username="username" class="avatar" @click="toggleMenu" />

    <div v-if="showMenu" class="dropdown">
      <!-- Holds internal links (VueJS routes) -->
      <router-link :to="accountItem.to" @click="toggleMenu">{{ accountItem.label }}</router-link>

      <!-- Opens the Paddle customer portal in a new tab, this is an anchor tag since we are already inside of a button -->
      <a href="#" @click.prevent="openSubscriptionPortal">{{ manageSubscriptionLabel }}</a>

      <router-link :to="supportItem.to" @click="toggleMenu">{{ supportItem.label }}</router-link>

      <!-- Holds external links (primarily Django routes) -->
      <a v-for="externalItem in externalMenuItems" :key="externalItem.label" :href="externalItem.href">
        {{ externalItem.label }}
      </a>
    </div>
  </button>
</template>

<style scoped>
/* TODO: Temporary fix for UserAvatar color bug */
.avatar {
  cursor: pointer;
  font-size: 0.8125rem;

  & :first-child {
    color: #eeeef0;
    /* var(--colour-ti-base) dark mode */
  }
}

.user-menu {
  position: relative;
  display: inline-block;
  background: none;
  border: none;
  font: inherit;
  padding: 0;

  .dropdown {
    position: absolute;
    right: 0;
    margin-top: 15.5rem;
    background: var(--colour-ti-base);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 0.5rem;
    box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.2);
    padding: 0.5rem 0;
    min-width: max-content;
    z-index: var(--z-index-header-dropdown);

    a {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      color: white;
      text-decoration: none;
      padding: 1rem 1.5rem;
      font-family: metropolis;
      font-size: 0.875rem;

      &:hover {
        background: rgba(255, 255, 255, 0.06);
      }
    }
  }
}
</style>
