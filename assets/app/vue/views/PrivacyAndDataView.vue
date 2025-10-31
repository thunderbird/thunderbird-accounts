<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { CheckboxInput, TextInput, DangerButton, VisualDivider, LinkButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import NeedSupportCard from '@/components/NeedSupportCard.vue';
import YourServices from '@/components/YourServices.vue';

/* TODO: Not in i18n yet as these are TBD */
const supportLinks = [
  { label: 'Need help with your account?', link: '#' },
  { label: 'Trouble receiving or sending emails?', link: '#' },
  { label: 'Change your email address', link: '#' },
  { label: 'Export your data', link: '#' },
];

const { t } = useI18n();
</script>

<template>
  <div class="privacy-and-data-view">
    <card-container class="delete-account-data-card">
      <h2>{{ t('views.privacyAndData.deleteAccountData') }}</h2>
  
      <div class="delete-account-data-card-content">
        <p>{{ t('views.privacyAndData.deleteAccountDataText') }}</p>
  
        <div>
          <strong>{{ t('views.privacyAndData.deleteAccountWill') }}</strong>
          <ul>
            <li>{{ t('views.privacyAndData.deleteAccountWillOne') }}</li>
            <li>{{ t('views.privacyAndData.deleteAccountWillTwo') }}</li>
          </ul>
        </div>
  
        <div>
          <strong>{{ t('views.privacyAndData.deleteAccountImportant') }}</strong>
          <ul>
            <li>{{ t('views.privacyAndData.deleteAccountImportantOne') }}</li>
            <li>{{ t('views.privacyAndData.deleteAccountImportantTwo') }}</li>
          </ul>
        </div>
  
        <div>
          <strong>{{ t('views.privacyAndData.deleteAccountExport') }}</strong>
  
          <checkbox-input
            :name="t('views.privacyAndData.deleteAccountCheckbox')"
            :label="t('views.privacyAndData.deleteAccountCheckbox')"
          />
        </div>
  
        <div class="delete-account-data-card-content-actions">
          <text-input
            name="password-confirmation"
            :required="true"
          >
            {{ t('views.privacyAndData.enterPassword') }}
          </text-input>
  
          <danger-button>{{ t('views.privacyAndData.deleteAccountButtonLabel') }}</danger-button>
          <router-link to="/dashboard" class="cancel-button">
            <link-button>
              {{ t('views.privacyAndData.cancelButtonLabel') }}
            </link-button>
          </router-link>
        </div>
      </div>
    </card-container>

    <visual-divider type="vertical" class="hidden-sm" />

    <div class="privacy-and-data-right-column">
      <your-services />
      <need-support-card :support-links="supportLinks" />
    </div>
  </div>
</template>

<style scoped>
.hidden-sm {
  display: none;
}

h2 {
  font-size: 1.5rem;
  font-weight: 500;
  font-family: metropolis;
  color: var(--colour-ti-highlight);
  margin-block-end: 1.5rem;
}

.privacy-and-data-view {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;
}

.delete-account-data-card {
  .delete-account-data-card-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    font-size: 0.875rem;
    line-height: 1.23;
    color: var(--colour-ti-secondary);

    strong {
      display: block;
      margin-block-end: 1.5rem;
    }

    ul {
      list-style-type: disc;
      padding-inline-start: 2.5rem;

      li + li {
        margin-block-start: 0.25rem;
      }
    }

    .delete-account-data-card-content-actions {
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: flex-end;
      column-gap: 1rem;

      .cancel-button {
        display: flex;
        justify-content: flex-end;
        grid-column: 2;

        button {
          padding: 0;
          margin-block-start: 0.875rem;
        }
      }
    }
  }
}

.privacy-and-data-right-column {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

@media (min-width: 1024px) {
  .hidden-sm {
    display: block;
  }

  .delete-account-data-card {
    max-width: 568px;
  }

  .privacy-and-data-view {
    flex-direction: row;
    gap: 2rem;
    justify-content: center;
  }

  .divider {
    align-self: stretch;
    height: auto;
  }
}
</style>