<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTimeoutFn } from '@vueuse/core';
import {
  BaseBadge,
  BaseBadgeTypes,
  CopyIcon,
  DangerButton,
  IconButton,
  LinkButton,
  NoticeBar,
  NoticeBarTypes,
  PrimaryButton,
  TextInput,
  ToolTip,
} from '@thunderbirdops/services-ui';
import { PhInfo, PhX } from '@phosphor-icons/vue';
import GenericModal from '@/components/GenericModal.vue';
import { APP_PASSWORD_SUPPORT_URL } from '@/defines';
import { createAppPassword, listAppPasswords, revokeAppPassword } from '../api';
import type { AppPasswordSummary, GeneratedAppPassword } from '../types';

const { t, d } = useI18n();

const KEY = 'views.mail.sections.emailSettings.appPasswordManager';

const revokeModal = useTemplateRef<InstanceType<typeof GenericModal>>('revokeModal');

const appPasswords = ref<AppPasswordSummary[]>([]);
// The mailbox username can differ from the sign-in email, so prefer what the server reports.
const username = ref<string>(window._page?.emailAddresses?.[0] || window._page?.userEmail || '');
const isLoading = ref(false);
const hasLoaded = ref(false);
const loadError = ref('');

const showCreateForm = ref(false);
const newName = ref('');
const isCreating = ref(false);
const createError = ref('');

const generated = ref<GeneratedAppPassword | null>(null);
const copyStatus = ref<'idle' | 'copied' | 'failed'>('idle');

const pendingRevoke = ref<AppPasswordSummary | null>(null);
const isRevoking = ref(false);
const revokeError = ref('');
const statusMessage = ref('');

const tooltipHovered = ref(false);
// Allow the pointer to cross the gap to the support link without enlarging the icon's hit area.
const { start: scheduleTooltipClose, stop: cancelTooltipClose } = useTimeoutFn(
  () => {
    tooltipHovered.value = false;
  },
  200,
  { immediate: false },
);
const openTooltip = () => {
  cancelTooltipClose();
  tooltipHovered.value = true;
};

const hasAppPasswords = computed(() => appPasswords.value.length > 0);
// One request at a time: loading counts as busy so no create/revoke can race the list that is about to replace it.
const isBusy = computed(() => isLoading.value || isCreating.value || isRevoking.value);
// Revoking is parked while a fresh secret is on screen so the user finishes the handoff first.
const revokeDisabled = computed(() => isBusy.value || generated.value !== null);

const displayName = (appPassword: AppPasswordSummary) => appPassword.name || t(`${KEY}.unnamed`);
const formatCreated = (createdAt: string) => d(new Date(createdAt), 'long');

const errorMessageFor = (error: unknown, fallbackKey: string) => {
  if (error instanceof Error && error.name === 'AuthSessionError') {
    return t(`${KEY}.sessionExpired`);
  }
  return t(fallbackKey);
};

const loadAppPasswords = async () => {
  if (isBusy.value) return;
  isLoading.value = true;
  loadError.value = '';

  try {
    const data = await listAppPasswords();
    if (!data.success) {
      loadError.value = data.error || t(`${KEY}.loadError`);
      return;
    }
    appPasswords.value = data.appPasswords ?? [];
    if (data.username) username.value = data.username;
    hasLoaded.value = true;
  } catch (error) {
    loadError.value = errorMessageFor(error, `${KEY}.loadError`);
  } finally {
    isLoading.value = false;
  }
};

const openCreateForm = () => {
  if (isBusy.value) return;
  createError.value = '';
  statusMessage.value = '';
  showCreateForm.value = true;
};

const cancelCreate = () => {
  showCreateForm.value = false;
  newName.value = '';
  createError.value = '';
};

const submitCreate = async () => {
  // Also covers a Retry of the list that is still running while the form stays open.
  if (isBusy.value) return;

  isCreating.value = true;
  createError.value = '';

  try {
    const data = await createAppPassword(newName.value.trim());

    if (!data.success || !data.secret || !data.appPassword) {
      createError.value = data.error || t(`${KEY}.genericError`);
      return;
    }

    if (data.username) username.value = data.username;
    // Additive: the new credential joins the list and other rows stay as they are. Stalwart reuses ids, so a stale
    // row with the same id (deleted elsewhere since the list loaded) takes the server's new metadata instead.
    const created = data.appPassword;
    const existingIndex = appPasswords.value.findIndex((appPassword) => appPassword.id === created.id);
    appPasswords.value =
      existingIndex === -1
        ? [...appPasswords.value, created]
        : appPasswords.value.map((appPassword, index) => (index === existingIndex ? created : appPassword));

    generated.value = {
      id: data.appPassword.id,
      name: data.appPassword.name || newName.value.trim(),
      secret: data.secret,
      username: username.value,
    };
    copyStatus.value = 'idle';
    showCreateForm.value = false;
    newName.value = '';
  } catch (error) {
    createError.value = errorMessageFor(error, `${KEY}.genericError`);
  } finally {
    isCreating.value = false;
  }
};

// Compose the standard copy control without CopyToClipboard, which logs its value and misses rejected writes.
const copySecret = async () => {
  if (!generated.value) return;
  try {
    await navigator.clipboard.writeText(generated.value.secret);
    copyStatus.value = 'copied';
  } catch {
    copyStatus.value = 'failed';
  }
};

const finishHandoff = () => {
  generated.value = null;
  copyStatus.value = 'idle';
};

const beginRevoke = (appPassword: AppPasswordSummary) => {
  if (revokeDisabled.value) return;
  pendingRevoke.value = appPassword;
  revokeError.value = '';
  statusMessage.value = '';
  revokeModal.value?.open();
};

const cancelRevoke = () => {
  if (isRevoking.value) return;
  revokeModal.value?.close();
};

// Runs for Cancel, the modal's close button and Escape alike (the modal stays put while a request is pending).
const onRevokeModalClosed = () => {
  pendingRevoke.value = null;
  revokeError.value = '';
};

const confirmRevoke = async () => {
  if (!pendingRevoke.value || isBusy.value) return;

  const target = pendingRevoke.value;
  isRevoking.value = true;
  revokeError.value = '';

  try {
    const data = await revokeAppPassword(target.id);

    // Only the explicit "already gone" code counts as done; any other 404 is a real failure.
    const alreadyGone = data.status === 404 && data.code === 'app_password_not_found';
    if (!data.success && !alreadyGone) {
      revokeError.value = data.error || t(`${KEY}.genericError`);
      return;
    }

    appPasswords.value = appPasswords.value.filter((appPassword) => appPassword.id !== target.id);
    statusMessage.value = t(`${KEY}.revoked`, { name: displayName(target) });
    pendingRevoke.value = null;
    revokeModal.value?.close();
  } catch (error) {
    revokeError.value = errorMessageFor(error, `${KEY}.genericError`);
  } finally {
    isRevoking.value = false;
  }
};

onMounted(loadAppPasswords);
</script>

<template>
  <div class="app-password-manager" data-testid="app-password-manager">
    <div class="app-password-set-indicator-container">
      <strong>{{ t('views.mail.sections.emailSettings.appPasswords') }}:</strong>
      <template v-if="hasLoaded">
        <base-badge v-if="hasAppPasswords" :type="BaseBadgeTypes.Set">
          {{ t('views.mail.sections.emailSettings.set') }}
        </base-badge>
        <base-badge v-else :type="BaseBadgeTypes.NotSet">
          {{ t('views.mail.sections.emailSettings.notSet') }}
        </base-badge>
      </template>
    </div>

    <p class="app-password-description">
      {{ t(`${KEY}.description`)
      }}<span
        class="info-tooltip-trigger"
        :class="{ 'tooltip-hovered': tooltipHovered }"
        tabindex="0"
        :aria-label="t(`${KEY}.moreInformation`)"
        @mouseenter="openTooltip"
        @mouseleave="scheduleTooltipClose()"
      >
        <ph-info size="16" aria-hidden="true" />
        <tool-tip :alt="t(`${KEY}.tooltip`)">
          <i18n-t :keypath="`${KEY}.tooltip`" tag="span">
            <template #supportUrl>
              <a :href="APP_PASSWORD_SUPPORT_URL" target="_blank" rel="noopener">{{
                t('views.mail.sections.emailSettings.appPasswordArticleTitle')
              }}</a>
            </template>
          </i18n-t>
        </tool-tip>
      </span>
    </p>

    <notice-bar v-if="loadError" :type="NoticeBarTypes.Critical" class="app-password-notice" role="alert">
      {{ loadError }}
      <template #cta>
        <link-button :disabled="isBusy" data-testid="app-password-retry" @click="loadAppPasswords">
          {{ t(`${KEY}.retry`) }}
        </link-button>
      </template>
    </notice-bar>

    <p v-if="isLoading && !hasAppPasswords" class="app-password-empty" role="status">{{ t(`${KEY}.loading`) }}</p>
    <ul v-else-if="hasAppPasswords" class="app-password-list" :aria-label="t(`${KEY}.listLabel`)">
      <li
        v-for="appPassword in appPasswords"
        :key="appPassword.id"
        class="app-password-item"
        data-testid="app-password-item"
      >
        <div class="app-password-meta">
          <span class="app-password-name">{{ displayName(appPassword) }}</span>
          <span v-if="appPassword.createdAt" class="app-password-created">
            {{ t(`${KEY}.created`) }}
            <time :datetime="appPassword.createdAt">{{ formatCreated(appPassword.createdAt) }}</time>
          </span>
        </div>
        <primary-button
          variant="outline"
          size="small"
          class="app-password-revoke"
          :aria-label="t(`${KEY}.revokeNamed`, { name: displayName(appPassword) })"
          :disabled="revokeDisabled"
          :data-id="appPassword.id"
          data-testid="app-password-revoke"
          @click="beginRevoke(appPassword)"
        >
          {{ t('views.manageMfa.actions.remove') }}
        </primary-button>
      </li>
    </ul>

    <notice-bar
      v-if="statusMessage"
      :type="NoticeBarTypes.Success"
      class="app-password-notice"
      role="status"
      data-testid="app-password-status"
    >
      {{ statusMessage }}
      <template #cta>
        <icon-button
          size="large"
          :aria-label="t('views.mail.sections.emailSettings.close')"
          @click="statusMessage = ''"
        >
          <ph-x size="24" aria-hidden="true" />
        </icon-button>
      </template>
    </notice-bar>

    <section
      v-if="generated"
      class="app-password-handoff"
      aria-labelledby="app-password-handoff-title"
      data-testid="app-password-handoff"
    >
      <h3 id="app-password-handoff-title">
        {{ t(`${KEY}.handoffTitle`, { name: generated.name }) }}
      </h3>
      <p>{{ t(`${KEY}.handoffInstruction`) }}</p>
      <dl class="app-password-credentials">
        <div>
          <dt>{{ t('views.mail.views.signUp.fields.username') }}</dt>
          <dd><code data-testid="app-password-username">{{ generated.username }}</code></dd>
        </div>
        <div>
          <dt>{{ t('views.mail.sections.emailSettings.appPassword') }}</dt>
          <dd><code class="app-password-secret" data-testid="generated-app-password">{{ generated.secret }}</code></dd>
        </div>
      </dl>
      <div class="app-password-actions">
        <link-button data-testid="copy-app-password" @click="copySecret">
          <template #iconLeft><copy-icon /></template>
          {{ t('views.mail.sections.emailSettings.copyGeneratedPassword') }}
        </link-button>
        <primary-button data-testid="app-password-done" @click="finishHandoff">
          {{ t(`${KEY}.done`) }}
        </primary-button>
      </div>
      <p
        class="app-password-copy-status"
        :class="{ failed: copyStatus === 'failed' }"
        role="status"
        aria-live="polite"
        data-testid="copy-status"
      >
        <template v-if="copyStatus === 'copied'">{{ t('views.manageMfa.modals.manageRecoveryCodes.copied') }}</template>
        <template v-else-if="copyStatus === 'failed'">{{ t(`${KEY}.copyFailed`) }}</template>
      </p>
    </section>

    <!-- novalidate: the backend owns validation and its messages are shown below the field. -->
    <form v-else-if="showCreateForm" class="app-password-form" novalidate @submit.prevent="submitCreate">
      <text-input
        v-model="newName"
        name="app-password-name"
        required
        autocomplete="off"
        :placeholder="t(`${KEY}.namePlaceholder`)"
        :help="t(`${KEY}.nameHelp`)"
        data-testid="app-password-name-input"
      >
        {{ t(`${KEY}.nameLabel`) }}
      </text-input>

      <notice-bar v-if="createError" :type="NoticeBarTypes.Critical" role="alert" data-testid="app-password-error">
        {{ createError }}
      </notice-bar>

      <div class="app-password-actions">
        <primary-button variant="outline" :disabled="isCreating" @click="cancelCreate">
          {{ t('views.mail.sections.emailSettings.cancel') }}
        </primary-button>
        <primary-button form-action="submit" :disabled="isBusy" data-testid="app-password-generate">
          {{ isCreating ? t(`${KEY}.generating`) : t(`${KEY}.generateButton`) }}
        </primary-button>
      </div>
    </form>

    <primary-button
      v-else
      variant="outline"
      class="app-password-create"
      :disabled="isBusy"
      data-testid="app-password-create"
      @click="openCreateForm"
    >
      {{ t('views.mail.sections.emailSettings.createPasswordButtonLabel') }}
    </primary-button>

    <generic-modal
      ref="revokeModal"
      :title="t(`${KEY}.revokeTitle`)"
      :dismissible="!isRevoking"
      @close="onRevokeModalClosed"
    >
      <template v-if="pendingRevoke">
        <p class="app-password-revoke-description" data-testid="revoke-description">
          {{ t(`${KEY}.revokeDescription`, { name: displayName(pendingRevoke) }) }}
        </p>

        <notice-bar v-if="revokeError" :type="NoticeBarTypes.Critical" class="app-password-notice" role="alert">
          {{ revokeError }}
        </notice-bar>
      </template>
      <template v-if="pendingRevoke" #actions>
        <primary-button variant="outline" :disabled="isRevoking" data-testid="cancel-revoke" @click="cancelRevoke">
          {{ t('views.mail.sections.emailSettings.cancel') }}
        </primary-button>
        <danger-button :disabled="isRevoking" data-testid="confirm-revoke" @click="confirmRevoke">
          {{ isRevoking ? t(`${KEY}.revoking`) : t(`${KEY}.confirmRevoke`) }}
        </danger-button>
      </template>
    </generic-modal>
  </div>
</template>

<style scoped>
.app-password-manager {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: var(--colour-ti-secondary);
  line-height: 1.32;

  strong {
    display: block;
    font-weight: 600;
    margin-block-end: 0.5rem;
  }

  p {
    margin: 0;
  }

  /* Plain inline flow so the info icon trails the last word instead of dropping onto its own row. The paragraph is
     the positioning context so the tooltip spans the panel instead of hanging off the icon and past the viewport. */
  .app-password-description {
    display: block;
    position: relative;
  }

  .app-password-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
  }

  .app-password-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 1rem;

    & + .app-password-item {
      border-block-start: 1px solid var(--colour-neutral-border);
    }
  }

  .app-password-meta {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
  }

  .app-password-name {
    color: var(--colour-ti-base);
    font-weight: 600;
    overflow-wrap: anywhere;
  }

  .app-password-created {
    font-size: 0.8125rem;
    color: var(--colour-ti-muted);
  }

  .app-password-revoke {
    flex-shrink: 0;
  }

  .app-password-create {
    align-self: flex-start;
  }

  .app-password-empty {
    color: var(--colour-ti-muted);
  }

  .app-password-handoff {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 0.5rem;
    background-color: var(--colour-neutral-lower);

    h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
      color: var(--colour-ti-base);
      overflow-wrap: anywhere;
    }
  }

  .app-password-credentials {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0;

    div {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    dt {
      font-size: 0.8125rem;
      color: var(--colour-ti-muted);
    }

    dd {
      margin: 0;
    }

    code {
      display: inline-block;
      max-width: 100%;
      padding: 0.375rem 0.5rem;
      border: 1px solid var(--colour-neutral-border);
      border-radius: 0.25rem;
      background-color: var(--colour-neutral-base);
      color: var(--colour-ti-base);
      font-size: 0.9375rem;
      overflow-wrap: anywhere;
      user-select: all;
    }
  }

  .app-password-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .app-password-copy-status {
    min-height: 1.32em;
    font-size: 0.875rem;
    color: var(--colour-ti-highlight);

    &.failed {
      color: var(--colour-ti-critical);
    }
  }

  .app-password-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .info-tooltip-trigger {
    display: inline-flex;
    align-items: center;
    vertical-align: text-bottom;
    margin-inline-start: 0.375rem;
    cursor: pointer;

    &:focus-visible {
      outline: 2px solid var(--colour-primary-default);
      outline-offset: 2px;
      border-radius: 999px;
    }
  }

  /* display:none while hidden keeps the tooltip out of layout, so it cannot widen the page on small screens. */
  .info-tooltip-trigger :deep(.tooltip) {
    display: none;
    width: auto;
    max-width: none;
    bottom: calc(100% + 0.5rem);
    left: 0;
    right: 0;
    top: auto;
    transform: none;
    font-size: 0.8125rem;
  }

  /* focus-within keeps the tooltip open while Tab moves from the icon onto the link inside it. */
  .info-tooltip-trigger.tooltip-hovered :deep(.tooltip),
  .info-tooltip-trigger:focus-within :deep(.tooltip),
  .info-tooltip-trigger :deep(.tooltip:hover) {
    display: block;
    visibility: visible;
    opacity: 1;
    cursor: default;
  }

  .info-tooltip-trigger :deep(.tooltip a) {
    color: var(--colour-ti-highlight);
  }
}

.app-password-revoke-description {
  color: var(--colour-ti-secondary);
  line-height: 1.32;
  text-align: center;
  overflow-wrap: anywhere;
}

.app-password-revoke-description + .app-password-notice {
  margin-block-start: 1rem;
}
</style>
