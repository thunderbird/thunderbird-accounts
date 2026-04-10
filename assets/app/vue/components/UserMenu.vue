<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useTemplateRef, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { UserAvatar } from '@thunderbirdops/services-ui';

defineProps<{
  username: string;
}>();

const { t } = useI18n();
const currentRoute = useRoute();
const isThundermail = computed(() => currentRoute.path.startsWith('/mail'));

const internalMenuItems = computed(() => {
  const items = [{
    label: t('components.userMenu.support'),
    to: '/contact',
  }]

  return items;
});

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
  <template v-if="isThundermail">
    <router-link to="/dashboard" class="user-avatar-link">
      <user-avatar :username="username" class="avatar" />
    </router-link>
  </template>
  <template v-else>
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
  </template>
</template>

<style scoped>
.user-avatar-link {
  text-decoration: none;
}

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
