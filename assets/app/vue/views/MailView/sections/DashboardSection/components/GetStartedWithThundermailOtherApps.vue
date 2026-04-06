<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhArrowSquareOut, PhQuestion, PhArrowRight, PhGear } from '@phosphor-icons/vue';
import { LinkButton } from '@thunderbirdops/services-ui';
import ActionCard from '@/components/ActionCard.vue';
import ServerSettingsCard from '@/components/ServerSettingsCard.vue';

const { t } = useI18n();
</script>

<template>
  <div class="action-cards">
    <!-- Automatic Configuration -->
    <action-card :title="t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.title')">
      <template #icon>
        <ph-arrow-square-out :size="20" />
      </template>

      <p class="action-description">
        {{ t('views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.descriptionOne') }}
      </p>

      <i18n-t keypath="views.mail.sections.dashboard.getStartedWithThundermail.otherAppsPanel.descriptionTwo" tag="p">
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
        <ph-question :size="20" />
      </template>
      <template #action>
        <link-button size="small" href="#" class="need-help-button">
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

  .action-description {
    margin-block-end: 1ch;
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