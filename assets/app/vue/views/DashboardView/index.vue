<script setup lang="ts">
import ThunderbirdApps from '@/components/ThunderbirdApps.vue';
import AccountCard from './components/AccountCard.vue';
import AccountDeletionCard from './components/AccountDeletionCard.vue';
import YourCurrentSubscription from './components/YourCurrentSubscription.vue';
import { PADDLE_TRANSACTION_STORAGE_KEY } from '@/defines';

// Just in case, attempt to empty the stored Paddle transaction id here too.
window.localStorage?.removeItem(PADDLE_TRANSACTION_STORAGE_KEY);
</script>

<script lang="ts">
export default {
  name: 'DashboardView',
};
</script>

<template>
  <div class="dashboard-view">
    <div class="dashboard-view-cards">
      <account-card />
      <account-deletion-card />
    </div>
    <div class="dashboard-view-cards">
      <thunderbird-apps />
      <your-current-subscription />
    </div>
  </div>
</template>

<style scoped>
.dashboard-view {
  display: flex;
  justify-content: center;
  gap: 2rem;
  flex-wrap: wrap;
  align-items: stretch;

  .dashboard-view-cards {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    gap: 2rem;
    max-width: none;
    width: 100%;
  }
}

@media (min-width: 768px) {
  .dashboard-view {
    gap: 4rem;

    .dashboard-view-cards {
      max-width: 568px;
      width: auto;
    }
  }
}

@media (min-width: 1024px) {
  .dashboard-view {
    gap: 2rem;
  }
}
</style>
