<script setup lang="ts">
import { VisualDivider } from '@thunderbirdops/services-ui';
import YourServices from '@/components/YourServices.vue';
import AccountCard from './components/AccountCard.vue';
import PrivacyAndDataCard from './components/PrivacyAndDataCard.vue';
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

@media (min-width: 1280px) {
  .hidden-sm {
    display: block;
  }

  .divider {
    align-self: stretch;
    height: auto;
  }
}
</style>