<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <section id="security-settings">
    <card-container>
      <h2>{{ t('views.mail.sections.securitySettings.securitySettings') }}</h2>

      <div class="security-settings-content">
        <div class="security-settings-left">
          <strong>{{ t('views.mail.sections.securitySettings.accountActivity') }}</strong>
          <p>{{ t('views.mail.sections.securitySettings.accountActivityDescriptionOne') }}</p>
          <p>{{ t('views.mail.sections.securitySettings.accountActivityDescriptionTwo') }}</p>
          <router-link to="/mail/security-settings">
            <primary-button variant="outline">{{ t('views.mail.sections.securitySettings.viewActivity') }}</primary-button>
          </router-link>
        </div>

        <div class="security-settings-right">
          <strong>{{ t('views.mail.sections.securitySettings.allowList') }}</strong>
          <p>{{ t('views.mail.sections.securitySettings.allowListDescription') }}</p>
          <router-link to="/mail/security-settings">
            <primary-button variant="outline">{{ t('views.mail.sections.securitySettings.manageAllowList') }}</primary-button>
          </router-link>
        </div>
      </div>
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

a {
  display: inline-block;
  text-decoration: none;
}

.security-settings-content {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
  color: var(--colour-ti-secondary);

  strong {
    display: block;
    font-weight: 600;
    letter-spacing: 0.48px;
    margin-block-end: 0.5rem;
  }

  p {
    line-height: 1.32;
    margin-block-end: 1rem;
  }
}
</style>