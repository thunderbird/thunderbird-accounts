<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhLifebuoy, PhArrowRight, PhGear } from '@phosphor-icons/vue';
import { LinkButton } from '@thunderbirdops/services-ui';
import ActionCard from '@/components/ActionCard.vue';
import ServerSettingsCard from '@/components/ServerSettingsCard.vue';
import { OTHER_APPS_SUPPORT_URL } from '@/defines';

const { t } = useI18n();
</script>

<template>
  <div class="action-cards">
    <!-- Automatic Configuration -->
    <action-card :title="t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.title')">
      <i18n-t keypath="views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.description" tag="p">
        <template #appPassword>
          <a href="#app-password-container" class="app-password-link">{{ t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.appPassword') }}</a>
        </template>
      </i18n-t>
    </action-card>

    <!-- Manual Configuration -->
    <action-card :title="t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.manualConfigurationTitle')">
      <template #icon>
        <ph-gear :size="20" />
      </template>

      <server-settings-card is-manual-configuration-section />
    </action-card>

    <!-- Need Help? -->
    <action-card
      :title="t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.needHelpTitle')"
      :description="t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.needHelpDescription')"
    >
      <template #icon>
        <ph-lifebuoy :size="20" />
      </template>
      <template #action>
        <link-button size="small" :href="OTHER_APPS_SUPPORT_URL" target="_blank" class="need-help-button">
          {{ t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.needHelpButtonLabel') }}

          <template #iconRight>
            <ph-arrow-right :size="16" />
          </template>
        </link-button>
      </template>
    </action-card>
  </div>
</template>

<style scoped>
.action-cards {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;

  p {
    font-size: 0.75rem;
    color: var(--colour-ti-secondary);
  }

  .app-password-link {
    text-decoration: underline;
    color: var(--colour-ti-secondary);
  }

  .need-help-button {
    color: var(--colour-primary-pressed);
    padding-inline-end: 0;
  }
}
</style>