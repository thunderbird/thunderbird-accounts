<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <section id="security-settings">
    <card-container>
      <h2>{{ t('views.mail.sections.securitySettings.securitySettings') }}</h2>
    </card-container>
  </section>
</template>

<style scoped>
h2 {
  font-size: 1.5rem;
  font-weight: 500;
  font-family: metropolis;
  color: var(--colour-ti-highlight);
  margin-block-end: 1.5rem;
}
</style>