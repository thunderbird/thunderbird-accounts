<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { BaseBadge, BaseBadgeTypes, LinkButton, PrimaryButton, VisualDivider } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <card-container class="my-account-card">
    <h2>{{ t('views.dashboard.accountCard.myAccount') }}</h2>

    <div class="my-account-card-details">
      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.email') }}</strong>
        <p>johnny.mneumonic@thundermail.com</p>
      </div>

      <visual-divider />

      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.password') }}</strong>
        <div class="my-account-card-field-with-link-button">
          <p>*********</p>
          <link-button>{{ t('views.dashboard.accountCard.change') }}</link-button>
        </div>
      </div>

      <visual-divider />

      <div class="my-account-card-field with-outline-button">
        <div>
          <strong>{{ t('views.dashboard.accountCard.mfa') }}</strong>
          <p>{{ t('views.dashboard.accountCard.on') }}</p>
        </div>

        <primary-button variant="outline" size="small">{{ t('views.dashboard.accountCard.manage') }}</primary-button>
      </div>

      <visual-divider />

      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.recoveryEmailAddress') }}</strong>
        <div class="my-account-card-field-with-link-button">
          <base-badge :type="BaseBadgeTypes.Set">{{ t('views.dashboard.accountCard.set') }}</base-badge>
          <link-button>{{ t('views.dashboard.accountCard.change') }}</link-button>
        </div>
      </div>

      <visual-divider />

      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.recoveryPhoneNumber') }}</strong>
        <div class="my-account-card-field-with-link-button">
          <base-badge :type="BaseBadgeTypes.Set">{{ t('views.dashboard.accountCard.set') }}</base-badge>
          <link-button>{{ t('views.dashboard.accountCard.change') }}</link-button>
        </div>
      </div>
    </div>
  </card-container>
</template>

<style scoped>
.my-account-card {
  min-width: 100%;
  color: var(--colour-ti-secondary);

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 1rem;
  }

  .my-account-card-details {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;

    .my-account-card-field {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;

      strong {
        font-weight: 600;
      }

      &.with-outline-button {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
      }

      .my-account-card-field-with-link-button {
        display: flex;
        align-items: center;
        justify-content: space-between;

        button {
          padding: 0;
        }
      }
    }
  }
}

@media (min-width: 1024px) {
  .my-account-card {
    min-width: 568px;
  }
}
</style>