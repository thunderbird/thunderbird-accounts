<script setup lang="ts">
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
const { t } = useI18n();

onMounted(() => {
  // After 5 seconds reload the page, if the payment came through they'll see the dashboard.
  window.setTimeout(() => {
    window.location.reload();
  }, 5000);
});
</script>

<template>
  <section class="pending-container">
    <h1 class="title">{{ t('views.subscribe.verification.title') }}</h1>
    <h3>{{ t('views.subscribe.verification.text') }}</h3>
    <i18n-t keypath="views.subscribe.verification.help" tag="p">
      <a href="/contact/">{{ t('views.subscribe.verification.support') }}</a>
    </i18n-t>
  </section>
</template>

<style scoped>
.pending-container {
  width: 100%;
  min-height: 50vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  text-align: center;

  .title {
    margin-bottom: 2rem;
  }
}
</style>
