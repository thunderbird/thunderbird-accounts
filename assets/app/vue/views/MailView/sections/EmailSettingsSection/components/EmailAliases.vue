<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes, BaseBadge, BaseBadgeTypes } from '@thunderbirdops/services-ui';
import { PhX } from '@phosphor-icons/vue';

// Local components
import EmailAliasActionsMenu from './EmailAliasActionsMenu.vue';
import EmailAliasForm from './EmailAliasForm.vue';

// Types
import { DOMAIN_STATUS } from '../../CustomDomainsSection/types';
import { EmailAlias } from '../types';

// API
import { addEmailAlias } from '../api';

const { t } = useI18n();

const aliasLimit = window._page?.maxEmailAliases;

const emailAliases = ref<EmailAlias[]>(window._page?.emailAddresses?.map((email, index) => ({
  email: email,
  // From Stalwart, primary / subscription email is always the first email address in the list
  isPrimary: index === 0,
  isSubscription: index === 0,
})) || []);
const isAddingEmailAlias = ref(false);
const errorMessage = ref<string>(null);

const allowedDomains = computed(() => {
  return window._page.customDomains
    ?.filter(domain => domain.status === DOMAIN_STATUS.VERIFIED)
    .map(domain => domain.name) || [];
});

const onAddAlias = async (emailAlias: string, domain: string) => {
  isAddingEmailAlias.value = true;

  try {
    const response = await addEmailAlias(emailAlias, domain);

    if (response.success) {
      emailAliases.value.push({ email: `${emailAlias}@${domain}`, isPrimary: false, isSubscription: false });
      errorMessage.value = null;
    } else {
      errorMessage.value = response.error;
    }
  } catch (error) {
    errorMessage.value = error;
  } finally {
    isAddingEmailAlias.value = false;
  }
};

const onDeleteAliasSuccess = (alias: EmailAlias) => {
  emailAliases.value = emailAliases.value.filter(item => item.email !== alias.email);
};

const onDeleteAliasError = (error: string) => {
  errorMessage.value = error;
};
</script>

<template>
  <div class="email-aliases-content">
    <div class="header-content">
      <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescription') }}</p>
      <p class="email-aliases-count-text">
        {{ t('views.mail.sections.emailSettings.emailAliasesDescriptionTwo', {
          aliasUsed: emailAliases.length, aliasLimit
        }) }}
      </p>
    </div>

    <!-- TODO: Uncomment when we have a way to change the primary email alias -->
    <!-- <notice-bar class="notice-bar-warning" :type="NoticeBarTypes.Warning">
      {{ t('views.mail.sections.emailSettings.emailAliasesPrimaryChangeWarning') }}
    </notice-bar> -->

    <div class="aliases-list">
      <div class="alias-item" v-for="alias in emailAliases" :key="alias.email">
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

        <email-alias-actions-menu
          :alias="alias"
          @delete-alias-success="onDeleteAliasSuccess"
          @delete-alias-error="onDeleteAliasError"
        />
      </div>
    </div>

    <notice-bar class="notice-bar-error" :type="NoticeBarTypes.Critical" v-if="errorMessage">
      <p>{{ errorMessage }}</p>

      <template #cta>
        <button @click="errorMessage = null">
          <ph-x size="16" />
        </button>
      </template>
    </notice-bar>

    <email-alias-form
      v-if="emailAliases.length < aliasLimit"
      :allowed-domains="allowedDomains"
      @add-alias="onAddAlias"
    />
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

  .notice-bar {
    margin-block-end: 1.5rem;

    button {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0.5rem;
      border: none;
      border-radius: 300px;
      box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05);
      background-color: rgba(0, 0, 0, 0.05);
      color: var(--colour-ti-secondary);
      cursor: pointer;

      &:hover {
        background-color: rgba(0, 0, 0, 0.1);
      }

      &:active {
        background-color: rgba(0, 0, 0, 0.2);
      }
    }
  }
}
</style>