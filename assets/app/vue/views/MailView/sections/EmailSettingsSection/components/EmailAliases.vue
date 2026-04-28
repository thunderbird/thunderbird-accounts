<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes, BaseBadge, BaseBadgeTypes, ToolTip } from '@thunderbirdops/services-ui';
import { PhX, PhInfo } from '@phosphor-icons/vue';

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
  domain: email.split('@')[1],
  // From Stalwart, primary / subscription email is always the first email address in the list
  isPrimary: index === 0,
  isSubscription: index === 0,
  isCatchAll: email.startsWith('@'),
})) || []);
const isAddingEmailAlias = ref(false);
const errorMessage = ref<string>(null);
console.log(emailAliases.value);
const allDomainOptions = computed(() => {
  // And the domains in the settings.ALLOWED_EMAIL_DOMAINS from the backend
  const allowedDomains = window._page.allowedDomains || [];

  return [...customDomains.value, ...allowedDomains];
});

/**
 * Display a list of catch-all aliases
 * These are aliases with no local part, there should only be a max of 1 per custom domain!
 */
const catchAlls = computed(() => {
  return emailAliases.value?.filter((val) => val?.email?.startsWith('@') ? val.email : null).map((val) => val.email) || [];
});

const sharedDomainAliases = computed(() => {
  return emailAliases.value?.filter((val) => window._page.allowedDomains.includes(val?.domain)).map((val) => val.email) || [];
});

/**
 * Allowed domains include any verified custom domains
 */
const customDomains = computed(() => window._page.customDomains
  ?.filter(domain => domain.status === DOMAIN_STATUS.VERIFIED)
  .map(domain => domain.name) || []);

const usedAliases = computed(() => (sharedDomainAliases.value?.length || 1) - 1);

const onAddAlias = async (emailAlias: string, domain: string) => {
  isAddingEmailAlias.value = true;

  try {
    const response = await addEmailAlias(emailAlias, domain);
    const isCatchAll = emailAlias === '*' || emailAlias === '';
    if (isCatchAll) {
      // This is cheating but it's the easiest way to do it.
      emailAlias = '';
    }

    if (response.success) {
      emailAliases.value.push({ email: `${emailAlias}@${domain}`, domain, isPrimary: false, isSubscription: false, isCatchAll });
      errorMessage.value = null;
    } else {
      errorMessage.value = response.error;
    }
  } catch (error) {
    errorMessage.value = error as string;
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
    <div id="tour-target-email-aliases" />

    <div id="email-aliases" class="header-content">
      <p>{{ t('views.mail.sections.emailSettings.emailAliasesDescription') }}</p>
      <div class="email-aliases-totals">
        <p class="email-aliases-count-text">
          {{ t('views.mail.sections.emailSettings.emailAliasesDescriptionTwo', {
            aliasUsed: usedAliases, aliasLimit
          }) }}
        </p>
        <span class="email-aliases-count-text">
          {{ t('views.mail.sections.emailSettings.catchAllUsed', {
            catchAllUsed: catchAlls.length, catchAllLimit: customDomains.length,
          }) }}
          <aside aria-labelledby="catch-all-tooltip" class="info-tooltip-trigger" tabindex="0">
            <ph-info size="13" />
            <tool-tip id="catch-all-tooltip" :alt="t('views.mail.sections.emailSettings.catchAllTooltip')">
              <i18n-t keypath="views.mail.sections.emailSettings.catchAllTooltip" tag="span">
                <template #supportUrl>
                  <!-- Uncomment when a support article exists. -->
                  <!--<a href="" target="_blank">{{ t('views.mail.sections.emailSettings.clickHere') }}</a>-->
                </template>
              </i18n-t>
            </tool-tip>
          </aside>
        </span>
      </div>
    </div>

    <!-- TODO: Uncomment when we have a way to change the primary email alias -->
    <!-- <notice-bar class="notice-bar-warning" :type="NoticeBarTypes.Warning">
      {{ t('views.mail.sections.emailSettings.emailAliasesPrimaryChangeWarning') }}
    </notice-bar> -->

    <div class="aliases-list" v-if="emailAliases.length > 0">
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

        <template v-if="alias.isCatchAll">
          <base-badge class="catch-all-badge" :type="BaseBadgeTypes.Default">
            {{ t('views.mail.sections.emailSettings.catchAll') }}
          </base-badge>
        </template>

        <email-alias-actions-menu v-if="!alias.isSubscription" :alias="alias"
          @delete-alias-success="onDeleteAliasSuccess" @delete-alias-error="onDeleteAliasError" />
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

    <email-alias-form v-if="emailAliases.length < aliasLimit" :all-domain-options="allDomainOptions"
      :existing-catch-alls="catchAlls" @add-alias="onAddAlias" />
  </div>
</template>

<style scoped>
#email-aliases {
  padding-inline: 0.5rem;
}

.email-aliases-content {
  line-height: 1.32;
  color: var(--colour-ti-secondary);
  padding-block-start: 0.25rem;

  .notice-bar-warning {
    margin-block-end: 1rem;
  }

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-block-end: 1.25rem;
  }

  .email-aliases-totals {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .email-aliases-count-text {
    font-style: italic;
    font-size: 0.75rem;
    color: var(--colour-ti-muted);
    line-height: normal;
  }

  .aliases-list {
    margin-block-end: 1.5rem;

    .alias-item {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      padding: 0.5rem;
      gap: 0.5rem;
      height: 100%;
      min-height: 60px;
      background-color: var(--colour-neutral-lower);

      &+.alias-item {
        background-color: transparent;
      }

      p {
        flex: 1;
        margin-block-end: 0;
      }
    }

    .catch-all-badge {
      /* Mixing hexcode with transparency... */
      background-color: color-mix(in srgb, var(--colour-accent-purple), transparent 80%);
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

  /* Stolen from AppPasswordSide, this should really be in tooltip itself though. */
  .info-tooltip-trigger {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    /* Small hack for alignment */
    top: 2px;

    &::before {
      content: '';
      position: absolute;
      bottom: 100%;
      left: 50%;
      width: max(100%, 18rem);
      height: 0.75rem;
      transform: translateX(-50%);
    }
  }

  .info-tooltip-trigger :deep(.tooltip) {
    visibility: hidden;
    opacity: 0;
    width: max-content;
    bottom: calc(100% + 0.5rem);
    left: 50%;
    top: auto;
    transform: translateX(-50%);
    font-size: 0.8125rem;
  }

  .info-tooltip-trigger:hover :deep(.tooltip),
  .info-tooltip-trigger :deep(.tooltip:hover) {
    visibility: visible;
    opacity: 1;
    cursor: default;
  }

  .info-tooltip-trigger :deep(.tooltip a) {
    color: var(--colour-ti-highlight);
  }
}
</style>
