<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <card-container class="privacy-and-data-card">
    <h2>{{ t('views.dashboard.privacyAndDataCard.privacyAndData') }}</h2>

    <div>
      <strong>{{ t('views.dashboard.privacyAndDataCard.deleteAccount') }}</strong>
      <p>{{ t('views.dashboard.privacyAndDataCard.deleteAccountText') }}</p>

      <router-link v-slot="{ href, navigate }" custom to="/contact">
        <primary-button :href="href" variant="outline" size="small" class="delete-account-button" @click="navigate">
          {{ t('views.dashboard.privacyAndDataCard.deleteAccountButtonLabel') }}
        </primary-button>
      </router-link>
    </div>
  </card-container>
</template>

<style scoped>
.privacy-and-data-card {
  min-width: unset;
  color: var(--colour-ti-secondary);

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 1rem;
  }

  strong {
    display: block;
    font-weight: 600;
    letter-spacing: 0.48px;
    margin-block-end: 0.5rem;
  }

  p {
    margin-block-end: 1rem;
    line-height: 1.32;
  }

  .delete-account-button {
    --button-outline-border: var(--critical-default);
    width: 13.625rem;
    height: 2.75rem;
    flex-grow: 0;
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    gap: 8px;
    padding: 1.125rem 1rem;
    border-radius: 8px;
    border: solid 1px var(--critical-default);
    background-color: var(--surface-base);
  }
}

@media (min-width: 1024px) {
  .privacy-and-data-card {
    min-width: 568px;
  }
}
</style>
