<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhSliders } from '@phosphor-icons/vue';
import { BaseBadge, BaseBadgeTypes, VisualDivider, PrimaryButton, LinkButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

const { t } = useI18n();

const userEmail = computed(() => window._page?.userEmail);
const userFullName = computed(() => window._page?.userFullName);
</script>

<template>
  <section id="email-settings">
    <card-container>
      <h2>{{ t('views.mail.sections.emailSettings.emailSettings') }}</h2>

      <div class="email-settings-content">
        <div class="email-settings-left">
          <div>
            <strong>{{ t('views.mail.sections.emailSettings.primaryEmail') }}:</strong>
            <p>{{ userEmail }}</p>
          </div>
  
          <div class="display-name-content">
            <div>
              <strong>{{ t('views.mail.sections.emailSettings.displayName') }}:</strong>
              <p>{{ userFullName }}</p>
            </div>
  
            <link-button>{{ t('views.mail.sections.emailSettings.change') }}</link-button>
          </div>
  
          <visual-divider />
  
          <div>
            <strong>{{ t('views.mail.sections.emailSettings.password') }}:</strong>
            <base-badge :type="BaseBadgeTypes.Set">{{ t('views.mail.sections.emailSettings.set') }}</base-badge>
          </div>
        </div>

        <div class="email-settings-right">
          <p>{{ t('views.mail.sections.emailSettings.changePasswordDescription') }}</p>
          <p>{{ t('views.mail.sections.emailSettings.changePasswordDescriptionTwo') }}</p>
          <primary-button variant="outline">{{ t('views.mail.sections.emailSettings.changePasswordButtonLabel') }}</primary-button>
        </div>
      </div>

      <details-summary :title="t('views.mail.sections.emailSettings.emailAliases')" default-open>
        <template #icon>
          <ph-sliders size="24" />
        </template>

        <div class="email-aliases-content">
          <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescription') }}</p>
          <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescriptionTwo', { aliasUsed: 3, aliasLimit: 10 }) }}</p>
        </div>
      </details-summary>
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

.email-settings-content {
  display: grid;
  grid-template-columns: 1fr;
  column-gap: 2rem;
  margin-block-end: 2.25rem;
  color: var(--colour-ti-secondary);
  
  .email-settings-left {
    display: flex;
    flex-direction: column;
    gap: 1rem;

    strong {
      display: block;
      font-weight: 600;
      margin-block-end: 0.25rem;
    }
  }

  .email-settings-right {
    p {
      margin-block-end: 1rem;
      line-height: 1.32;
      color: var(--colour-ti-secondary);
    }
  }

  .display-name-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
}

.email-aliases-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  line-height: 1.32;
  color: var(--colour-ti-secondary);

  & :last-child {
    font-style: italic;
    font-size: 0.75rem;
    color: var(--colour-ti-muted);
    line-height: normal;
  }
}

@media (min-width: 768px) {
  .email-settings-content {
    grid-template-columns: 50% 50%;
  }
}
</style>