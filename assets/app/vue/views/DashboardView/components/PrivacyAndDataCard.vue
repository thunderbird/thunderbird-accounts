<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { LinkButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <card-container class="privacy-and-data-card">
    <h2>{{ t('views.dashboard.privacyAndDataCard.privacyAndData') }}</h2>

    <div class="privacy-and-data-card-details">
      <!-- TODO: Uncomment when implementing device management -->
      <!-- <div>
        <strong>{{ t('views.dashboard.privacyAndDataCard.manageDevices') }}</strong>
        <p>{{ t('views.dashboard.privacyAndDataCard.manageDevicesText') }}</p>
    
        <div class="manage-devices-buttons">
          <primary-button variant="outline">{{ t('views.dashboard.privacyAndDataCard.manageDevicesButtonLabel') }}</primary-button>
          <link-button>{{ t('views.dashboard.privacyAndDataCard.logoutFromAllDevicesButtonLabel') }}</link-button>
        </div>
      </div>
  
      <visual-divider /> -->
  
      <div>
        <strong>{{ t('views.dashboard.privacyAndDataCard.deleteAccount') }}</strong>
        <p>{{ t('views.dashboard.privacyAndDataCard.deleteAccountText') }}</p>

        <a href="/contact/">
          <link-button size="small" class="delete-account-button">
            {{ t('views.dashboard.privacyAndDataCard.deleteAccountButtonLabel') }}
          </link-button>
        </a>
      </div>
    </div>
  </card-container>
</template>

<style scoped>
.privacy-and-data-card {
  min-width: unset;
  color: var(--colour-ti-secondary);

  .privacy-and-data-card-details {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

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

  .manage-devices-buttons {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .delete-account-button {
    padding-inline: 0;
  }
}

@media (min-width: 1024px) {
  .privacy-and-data-card {
    min-width: 568px;
  }
}
</style>