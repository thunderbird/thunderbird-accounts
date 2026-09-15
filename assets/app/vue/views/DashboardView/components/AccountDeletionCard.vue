<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <card-container class="account-deletion-card">
    <h2>{{ t('views.dashboard.accountDeletionCard.heading') }}</h2>
  
    <div class="account-deletion-card-details">
      <strong>{{ t('views.dashboard.accountDeletionCard.subheading') }}</strong>
      <p>{{ t('views.dashboard.accountDeletionCard.description') }}</p>
      <router-link to="/contact" class="delete-account-link">
        {{ t('views.dashboard.accountDeletionCard.buttonLabel') }}
      </router-link>
    </div>
  </card-container>
</template>

<style scoped>
.account-deletion-card {
  min-width: unset;
  color: var(--colour-ti-secondary);

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 2rem;
  }

  .account-deletion-card-details {
    p {
      margin-block-end: 1rem;
      line-height: 1.32;
    }

    strong {
      display: block;
      font-weight: 600;
      letter-spacing: 0.48px;
      margin-block-end: 0.5rem;
    }
  }

  .delete-account-link {
    display: inline;
    font-size: 0.75rem;
    color: var(--colour-ti-critical);

    &:focus-visible {
      outline: .125rem solid var(--colour-primary-default);
      outline-offset: .125rem;
      border-radius: 0.5rem;
    }
  }
}

@media (min-width: 1024px) {
  .account-deletion-card {
    min-width: 568px;
  }
}
</style>
