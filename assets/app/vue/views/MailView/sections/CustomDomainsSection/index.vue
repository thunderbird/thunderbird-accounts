<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<script lang="ts">
export default {
  name: 'CustomDomainsSection',
};
</script>

<template>
  <section id="custom-domains">
    <card-container>
      <h2>{{ t('views.mail.sections.customDomains.customDomains') }}</h2>
      <p>{{ t('views.mail.sections.customDomains.customDomainsDescription') }}</p>
      <strong>{{ t('views.mail.sections.customDomains.domainsAdded', { domainCount: 2, domainLimit: 3 }) }}</strong>
    </card-container>
  </section>
</template>

<style scoped>
h2 {
  font-size: 1.5rem;
  font-weight: 500;
  font-family: metropolis;
  color: var(--colour-ti-highlight);
  margin-block-end: 0.25rem;
}

p {
  font-family: Inter;
  line-height: 1.32;
  color: var(--colour-ti-secondary);
  margin-block-end: 1.5rem;
}

strong {
  font-family: Inter;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.48px;
  color: var(--colour-ti-secondary);
}
</style>
