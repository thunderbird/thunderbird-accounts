<script setup lang="ts">
import { ref } from 'vue';
import ThunderbirdApps from '@/components/ThunderbirdApps.vue';
import WelcomeHeader from './components/WelcomeHeader.vue';
import GetStartedWithThundermail from './components/GetStartedWithThundermail.vue';
import AccountCard from './components/AccountCard.vue';
import AccountDeletionCard from './components/AccountDeletionCard.vue';
import YourCurrentSubscription from './components/YourCurrentSubscription.vue';
import { PADDLE_TRANSACTION_STORAGE_KEY } from '@/defines';

// Just in case, attempt to empty the stored Paddle transaction id here too.
window.localStorage?.removeItem(PADDLE_TRANSACTION_STORAGE_KEY);

const isGetStartedPinned = ref(true);
</script>

<script lang="ts">
export default {
  name: 'DashboardView',
};
</script>

<template>
  <div class="dashboard-view">
    <welcome-header />

    <div class="dashboard-view-content">
      <div class="dashboard-view-cards">
        <div id="get-started-pinned-slot" class="teleport-target" />
        <account-card />
        <account-deletion-card />
        <div id="get-started-unpinned-slot" class="teleport-target" />
      </div>
      <div class="dashboard-view-cards">
        <thunderbird-apps />
        <your-current-subscription />
      </div>
    </div>

    <Teleport defer :to="isGetStartedPinned ? '#get-started-pinned-slot' : '#get-started-unpinned-slot'">
      <get-started-with-thundermail
        :is-pinned="isGetStartedPinned"
        @toggle-pinned="isGetStartedPinned = !isGetStartedPinned"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
}

.dashboard-view-content {
  display: grid;
  grid-template-columns: 1fr;
  justify-content: center;
  justify-items: center;
  gap: 2rem;

  .dashboard-view-cards {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    gap: 2rem;
    max-width: none;
    width: 100%;
  }
}

.teleport-target {
  display: contents;
}

@media (min-width: 768px) {
  .dashboard-view-content {
    .dashboard-view-cards {
      max-width: 568px;
    }
  }
}

@media (min-width: 1024px) {
  .dashboard-view-content {
    /* Resolves to px at max-width 968px */
    grid-template-columns: minmax(0, 591fr) minmax(0, 345fr);
    justify-items: stretch;
    gap: 2rem;
    max-width: 968px;
    width: 100%;
    margin-inline: auto;

    .dashboard-view-cards {
      max-width: none;
    }
  }
}
</style>
