<script setup lang="ts">
import WelcomeHeader from './components/WelcomeHeader.vue';
import GetStartedWithThundermail from './components/GetStartedWithThundermail.vue';
</script>

<script lang="ts">
export default {
  name: 'DashboardSection',
};
</script>

<template>
  <section id="dashboard">
    <welcome-header />
    <get-started-with-thundermail />
  </section>
</template>