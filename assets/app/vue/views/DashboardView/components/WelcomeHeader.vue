<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import MailStorageProgress from '@/views/DashboardView/components/MailStorageProgress.vue';
import SendStorageProgress from '@/views/DashboardView/components/SendStorageProgress.vue';

const { t } = useI18n();

// From Stalwart, primary email is always the first email address in the list
const primaryEmail = computed(() => window._page?.emailAddresses?.[0] || '');
const userDisplayName = computed(() => window._page?.userDisplayName);
</script>

<template>
  <div class="welcome-header">
    <div class="welcome-container">
      <p class="welcome">{{ t('views.mail.sections.dashboard.welcomeHeader.welcome') }},</p>
      <p class="name">{{ userDisplayName }}</p>
      <p class="email">{{ primaryEmail }}</p>
    </div>

    <div class="plan-info-container">
      <mail-storage-progress />
      <send-storage-progress />
    </div>
  </div>
</template>

<style scoped>
.welcome-header {
  display: grid;
  grid-template-columns: 1fr;
  grid-auto-flow: row;
  row-gap: 2rem;
  column-gap: 1.6875rem;
  align-items: center;
  margin-block-end: 2.5rem;
}

.welcome-container {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-family: metropolis;

  .welcome {
    text-transform: uppercase;
    font-size: 0.875rem;
    letter-spacing: 0.42px;
    color: var(--colour-ti-muted);
  }

  .name {
    font-size: 2.25rem;
    line-height: 1.2;
    letter-spacing: -0.36px;
    color: var(--colour-ti-base);
  }

  .email {
    font-family: Inter;
    font-size: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
  }
}

.plan-info-container {
  color: var(--colour-ti-secondary);
  width: 100%;
  margin-block-end: 0.5rem;
}

@media (min-width: 768px) {
  .welcome-header {
    width: 100%;
    max-width: 568px;
    margin-inline: auto;
  }
}

@media (min-width: 1024px) {
  .welcome-header {
    grid-template-columns: 1fr 1fr;
    width: 100%;
    max-width: 968px;
    margin-inline: auto;
  }
}
</style>
