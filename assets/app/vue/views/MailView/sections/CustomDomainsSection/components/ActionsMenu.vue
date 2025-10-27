<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDotsThreeVertical } from '@phosphor-icons/vue';

import { verifyDomain } from '../api'

const props = defineProps<{
  domain: {
    name: string;
    status: string;
    emailsCount?: number;
  };
}>();

const showMenu = ref(false);
const menuRef = ref<HTMLElement | null>(null);

const { t } = useI18n();

const toggleMenu = () => {
  showMenu.value = !showMenu.value;
};

const handleRetry = async () => {
  await verifyDomain(props.domain.name);
  showMenu.value = false;
};

const handleDelete = () => {
  // TODO: Implement delete functionality
  console.log('Delete clicked', props.domain);
  showMenu.value = false;
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
  <div class="actions-menu" ref="menuRef">
    <button class="kebab-menu-button" @click="toggleMenu">
      <ph-dots-three-vertical size="20" />
    </button>

    <div v-if="showMenu" class="dropdown">
      <button @click="handleRetry">{{ t('views.mail.sections.customDomains.retry') }}</button>
      <button @click="handleDelete">{{ t('views.mail.sections.customDomains.delete') }}</button>
    </div>
  </div>
</template>

<style scoped>
.actions-menu {
  position: relative;
  display: inline-block;
}

.kebab-menu-button {
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  color: inherit;
  cursor: pointer;
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
  z-index: 10;

  button {
    display: block;
    width: 100%;
    background: none;
    border: none;
    color: white;
    text-align: left;
    padding: 1rem 1.5rem;
    font-family: metropolis;
    font-size: 0.875rem;
    cursor: pointer;

    &:hover {
      background: rgba(255, 255, 255, 0.06);
    }
  }
}
</style>