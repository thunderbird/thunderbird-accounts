<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { UserAvatar } from '@thunderbirdops/services-ui';

defineProps<{
  username: string;
}>();

const { t } = useI18n();

const internalMenuItems = [
  {
    label: t('components.userMenu.account'),
    to: '/dashboard',
  },
  {
    label: t('components.userMenu.support'),
    to: '/contact',
  },
]

const externalMenuItems = [
  {
    label: t('components.userMenu.logout'),
    href: '/logout/',
  },
];

const showMenu = ref(false);
const menuRef = ref<HTMLElement | null>(null);

const toggleMenu = () => {
  showMenu.value = !showMenu.value;
};
</script>

<template>
  <button class="user-menu" ref="menuRef">
    <user-avatar :username="username" class="avatar" @click="toggleMenu" />

    <div v-if="showMenu" class="dropdown">
      <!-- Holds internal links (VueJS routes) -->
      <router-link v-for="internalItem in internalMenuItems" :key="internalItem.label" :to="internalItem.to"
        @click="toggleMenu">
        {{ internalItem.label }}
      </router-link>

      <!-- Holds external links (primarily Django routes) -->
      <a v-for="externalItem in externalMenuItems" :key="externalItem.label" :href="externalItem.href">
        {{ externalItem.label }}
      </a>
    </div>
  </button>
  <div v-if="showMenu" @click="toggleMenu" id="fullscreen-clickbox" />
</template>

<style scoped>
#fullscreen-clickbox {
  width: 100vw;
  height: 100vh;
  top: 0;
  left: 0;
  position: fixed;
  z-index: var(--z-index-fullscreen-clickbox);
}

.user-menu {
  position: relative;
  display: inline-block;
  background: none;
  border: none;
  cursor: pointer;

  /* TODO: Temporary fix for UserAvatar color bug */
  .avatar {
    & :first-child {
      color: #eeeef0;
      /* var(--colour-ti-base) dark mode */
    }
  }

  .dropdown {
    position: absolute;
    right: 0;
    margin-top: 0.5rem;
    background: var(--colour-ti-base);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 0.5rem;
    box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.2);
    padding: 0.5rem 0;
    min-width: 150px;
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
