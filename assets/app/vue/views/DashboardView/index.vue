<script setup lang="ts">
import { VisualDivider } from '@thunderbirdops/services-ui';
import AccountCard from './components/AccountCard.vue';
import PrivacyAndDataCard from './components/PrivacyAndDataCard.vue';
import YourServices from './components/YourServices.vue';
import YourCurrentSubscription from './components/YourCurrentSubscription.vue';
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
      <privacy-and-data-card />
    </div>

    <visual-divider type="vertical" class="hidden-sm" />

    <div class="dashboard-view-cards">
      <your-services />
      <your-current-subscription />
    </div>
  </div>
</template>

<style scoped>
.hidden-sm {
  display: none;
}

.dashboard-view {
  display: flex;
  justify-content: center;
  gap: 2.5rem;
  flex-wrap: wrap;

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
    .dashboard-view-cards {
      max-width: 568px;
      width: auto;
    }
  }
}

@media (min-width: 1280px) {
  .hidden-sm {
    display: block;
  }
}
</style>