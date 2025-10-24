<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes, BaseBadge, BaseBadgeTypes } from '@thunderbirdops/services-ui';

// Local components
import EmailAliasActionsMenu from './EmailAliasActionsMenu.vue';
import EmailAliasForm from './EmailAliasForm.vue';

// Types
import { EmailAlias } from '../types';

const { t } = useI18n();

const allowedDomains = ['customdomain.lol', 'davitest.com'];
const aliasLimit = 10;

const placeholderAliases = ref<EmailAlias[]>([
  { id: 1, email: 'username@thundermail.com', isPrimary: true, isSubscription: true },
  { id: 2, email: 'username2@tb.pro', isPrimary: false, isSubscription: false },
  { id: 3, email: 'ryan@sipes.us', isPrimary: false, isSubscription: false },
]);

const onAddAlias = (emailAlias: string, domain: string) => {
  placeholderAliases.value.push({
    id: placeholderAliases.value.length + 1,
    email: `${emailAlias}@${domain}`, isPrimary: false, isSubscription: false
  });
};

const onMakePrimary = (alias: EmailAlias) => {
  placeholderAliases.value = placeholderAliases.value.map(item => ({
    ...item,
    isPrimary: item.id === alias.id
  }));
};

const onDeleteAlias = (alias: EmailAlias) => {
  placeholderAliases.value = placeholderAliases.value.filter(item => item.id !== alias.id);

  // Make the subscription alias the primary one if there is no primary alias
  if (placeholderAliases.value.every(item => !item.isPrimary)) {
    placeholderAliases.value = placeholderAliases.value.map(item => ({
      ...item,
      isPrimary: item.isSubscription
    }));
  }
};
</script>

<template>
  <div class="email-aliases-content">
    <div class="header-content">
      <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescription') }}</p>
      <p class="email-aliases-count-text">{{ t('views.mail.sections.emailSettings.emailAliasesDescriptionTwo', { aliasUsed: placeholderAliases.length, aliasLimit }) }}</p>
    </div>

    <notice-bar class="notice-bar-warning" :type="NoticeBarTypes.Warning">
      {{ t('views.mail.sections.emailSettings.emailAliasesPrimaryChangeWarning') }}
    </notice-bar>

    <div class="aliases-list">
      <div class="alias-item" v-for="alias in placeholderAliases" :key="alias.id">
        <p>{{ alias.email }}</p>

        <template v-if="alias.isPrimary">
          <base-badge :type="BaseBadgeTypes.Primary">
            {{ t('views.mail.sections.emailSettings.primary') }}
          </base-badge>
        </template>

        <template v-if="alias.isSubscription">
          <base-badge :type="BaseBadgeTypes.Subscription">
            {{ t('views.mail.sections.emailSettings.subscription') }}
          </base-badge>
        </template>

        <email-alias-actions-menu :alias="alias" @make-primary="onMakePrimary" @delete-alias="onDeleteAlias" />
      </div>
    </div>

    <email-alias-form :allowed-domains="allowedDomains" @add-alias="onAddAlias" v-if="placeholderAliases.length < aliasLimit" />
  </div>
</template>

<style scoped>
.email-aliases-content {
  line-height: 1.32;
  color: var(--colour-ti-secondary);

  .notice-bar-warning {
    margin-block-end: 1rem;
  }

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-block-end: 1rem;
  }

  .email-aliases-count-text {
    font-style: italic;
    font-size: 0.75rem;
    color: var(--colour-ti-muted);
    line-height: normal;
  }

  .aliases-list {
    border-block-start: 1px solid var(--colour-neutral-border);
    border-block-end: 1px solid var(--colour-neutral-border);
    margin-block-end: 1.5rem;

    .alias-item {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      padding: 1rem 0.5rem;
      gap: 0.5rem;
      height: 100%;
      min-height: 60px;

      & + .alias-item {
        border-block-start: 1px solid var(--colour-neutral-border);
      }

      p {
        flex: 1;
        margin-block-end: 0;
      }
    }
  }
}
</style>