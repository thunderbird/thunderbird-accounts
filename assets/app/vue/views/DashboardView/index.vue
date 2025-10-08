<script setup lang="ts">
import AccountCard from './components/AccountCard.vue';
import PrivacyAndDataCard from './components/PrivacyAndDataCard.vue';
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
  </div>
</template>

<style scoped>
.dashboard-view {
  display: flex;
  gap: 2rem;
  
  .dashboard-view-cards {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }
}
</style>