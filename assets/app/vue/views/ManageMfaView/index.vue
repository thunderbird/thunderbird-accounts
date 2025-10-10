<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { VisualDivider } from '@thunderbirdops/services-ui';
import NeedSupportCard from '@/components/NeedSupportCard.vue';
import AuthenticationMethods from './components/AuthenticationMethods.vue';

const { t } = useI18n();

/* TODO: Not in i18n yet as these are TBD */
const supportLinks = [
  { label: 'How to Set Up Multi-Factor Authentication (MFA)', link: '#' },
  { label: 'Recovering Access If You Lose Your MFA Device', link: '#' },
  { label: 'Managing Your MFA Methods (Phone, Email, App)', link: '#' },
  { label: 'Understanding Backup Codes and How To Use Them', link: '#' },
];
</script>

<script lang="ts">
export default {
  name: 'ManageMfaView',
};
</script>

<template>
  <div class="manage-mfa-view">
    <div class="manage-mfa-view-left-column">
      <h2>{{ t('views.manageMfa.multiFactorAuthentication') }}</h2>
  
      <p>
        {{ t('views.manageMfa.multiFactorAuthenticationDescription') }}
        <a href="#">{{ t('views.manageMfa.multiFactorAuthenticationLearnMore') }}</a>
      </p>

      <authentication-methods />
    </div>

    <visual-divider type="vertical" class="hidden-sm" />

    <div class="manage-mfa-view-right-column">
      <need-support-card :support-links="supportLinks" />
    </div>
  </div>
</template>

<style scoped>
.manage-mfa-view {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;

  .manage-mfa-view-left-column {
    h2 {
      font-family: metropolis;
      font-size: 1.5rem;
      font-weight: 500;
      color: var(--colour-ti-highlight);
      margin-block-end: 1rem;
    }

    p {
      line-height: 1.32;
      color: var(--colour-ti-base);
      margin-block-end: 2rem;

      a {
        color: var(--colour-ti-highlight);
      }
    }
  }

  .manage-mfa-view-right-column {
    max-width: 345px;
  }
}


@media (min-width: 1024px) {
  .hidden-sm {
    display: block;
  }

  .divider {
    align-self: stretch;
    height: auto;
  }

  .manage-mfa-view {
    flex-direction: row;
    gap: 2rem;

    .manage-mfa-view-left-column {
      max-width: 567px;
    }
  }
}
</style>
