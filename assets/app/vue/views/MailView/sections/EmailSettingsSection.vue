<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhSliders } from '@phosphor-icons/vue';
import {
  BaseBadge,
  BaseBadgeTypes,
  VisualDivider,
  PrimaryButton,
  LinkButton,
  TextInput,
  NoticeBar,
  NoticeBarTypes
} from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

const { t } = useI18n();

// Password form
const showPasswordForm = ref(false);
const appPassword = ref<string | null>(null);
const appPasswordConfirm = ref<string | null>(null);
const errorMessage = ref(window._page?.formError || '');
const successMessage = ref<string | null>(null);
const isSubmitting = ref(false);

// Display name form
const showDisplayNameForm = ref(false);
const displayName = ref<string | null>(null);
const errorMessageDisplayName = ref(window._page?.formError || '');
const isSubmittingDisplayName = ref(false);

const userEmail = computed(() => window._page?.userEmail);
const userDisplayName = computed(() => window._page?.userDisplayName);

const appPasswords = window._page?.appPasswords || [];

const onSetPasswordSubmit = async () => {
  if (isSubmitting.value) return;

  if (appPassword.value !== appPasswordConfirm.value) {
    errorMessage.value = t('views.mail.sections.emailSettings.passwordsDoNotMatch');
    return;
  }

  errorMessage.value = '';
  isSubmitting.value = true;

  try {
    const response = await fetch('/self-serve/app-passwords/set', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window._page.csrfToken,
      },
      body: JSON.stringify({
        name: userEmail.value,
        password: appPassword.value,
      }),
    });

    const data = await response.json();

    if (data.success) {
      // Reset form and close
      appPassword.value = '';
      showPasswordForm.value = false;

      successMessage.value = t('views.mail.sections.emailSettings.passwordSetSuccessfully');

      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } else {
      errorMessage.value = data.error || t('views.mail.sections.emailSettings.anErrorOccurred');
    }
  } catch (error) {
    console.error('Error changing password:', error);
    errorMessage.value = t('views.mail.sections.emailSettings.anErrorOccurredWhileChangingPassword');
  } finally {
    isSubmitting.value = false;
  }
};

const onSetDisplayNameSubmit = async () => {
  if (isSubmittingDisplayName.value) return;

  errorMessageDisplayName.value = '';
  isSubmittingDisplayName.value = true;

  try {
    const response = await fetch('/self-serve/display-name/set', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window._page.csrfToken,
      },
      body: JSON.stringify({
        'display-name': displayName.value,
      }),
    });

    const data = await response.json();

    if (data.success) {
      // Reset form and close
      displayName.value = '';
      showDisplayNameForm.value = false;

      // Reload the page to reflect changes
      window.location.reload();
    } else {
      errorMessageDisplayName.value = data.error || t('views.mail.sections.emailSettings.anErrorOccurred');
    }
  } catch (error) {
    console.error('Error changing display name:', error);
    errorMessageDisplayName.value = t('views.mail.sections.emailSettings.anErrorOccurredWhileChangingDisplayName');
  } finally {
    isSubmittingDisplayName.value = false;
  }
};

const onCancelSetPassword = () => {
  errorMessage.value = '';
  appPassword.value = '';
  showPasswordForm.value = false;
};

const onCancelSetDisplayName = () => {
  errorMessageDisplayName.value = '';
  displayName.value = '';
  showDisplayNameForm.value = false;
};
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
            <template v-if="showDisplayNameForm">
              <form
                method="post"
                action="/self-serve/display-name/set"
              >
                <text-input v-model="displayName" name="display-name" data-testid="display-name-input">
                  {{ t('views.mail.sections.emailSettings.newDisplayName') }}:
                </text-input>

                <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessageDisplayName">{{ errorMessageDisplayName }}</notice-bar>

                <div class="set-display-name-buttons-container">
                  <primary-button variant="outline" @click="onCancelSetDisplayName" :disabled="isSubmittingDisplayName">{{ t('views.mail.sections.emailSettings.cancel') }}</primary-button>
                  <primary-button @click="onSetDisplayNameSubmit" :disabled="isSubmittingDisplayName" data-testid="display-name-set-btn">
                    {{ isSubmittingDisplayName ? t('views.mail.sections.emailSettings.saving') : t('views.mail.sections.emailSettings.save') }}
                  </primary-button>
                </div>
              </form>
            </template>
            <template v-else>
              <div>
                <strong>{{ t('views.mail.sections.emailSettings.displayName') }}:</strong>
                <p>{{ userDisplayName }}</p>
              </div>

              <link-button @click="showDisplayNameForm = true">{{ t('views.mail.sections.emailSettings.change') }}</link-button>
            </template>
          </div>
  
          <visual-divider />
  
          <div>
            <strong>{{ t('views.mail.sections.emailSettings.password') }}:</strong>
            <template v-if="appPasswords.length > 0">
              <base-badge :type="BaseBadgeTypes.Set">{{ t('views.mail.sections.emailSettings.set') }}</base-badge>
            </template>
            <template v-else>
              <base-badge :type="BaseBadgeTypes.NotSet">{{ t('views.mail.sections.emailSettings.notSet') }}</base-badge>
            </template>
          </div>
        </div>

        <div class="email-settings-right">
          <p>{{ t('views.mail.sections.emailSettings.changePasswordDescription') }}</p>
          <p>{{ t('views.mail.sections.emailSettings.changePasswordDescriptionTwo') }}</p>

          <notice-bar :type="NoticeBarTypes.Success" v-if="successMessage" class="success-message">{{ successMessage }}</notice-bar>

          <template v-if="showPasswordForm">
            <form
              ref="appPasswordFormRef"
              method="post"
              action="/self-serve/app-passwords/set"
            >
              <input type="hidden" name="name" :value="userEmail" />

              <text-input v-model="appPassword" name="password" type="password" data-testid="app-passwords-add-password-input">
                {{ t('views.mail.sections.emailSettings.newPassword') }}:
              </text-input>

              <text-input v-model="appPasswordConfirm" name="password-confirm" type="password" data-testid="app-passwords-add-password-confirm-input">
                {{ t('views.mail.sections.emailSettings.confirmPassword') }}:
              </text-input>

              <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">{{ errorMessage }}</notice-bar>

              <div class="set-password-buttons-container">
                <primary-button variant="outline" @click="onCancelSetPassword" :disabled="isSubmitting">{{ t('views.mail.sections.emailSettings.cancel') }}</primary-button>
                <primary-button @click="onSetPasswordSubmit" :disabled="isSubmitting" data-testid="app-passwords-add-btn">
                  {{ isSubmitting ? t('views.mail.sections.emailSettings.saving') : t('views.mail.sections.emailSettings.save') }}
                </primary-button>
              </div>
            </form>
          </template>
          <template v-else-if="appPasswords.length > 0">
            <primary-button variant="outline" @click="showPasswordForm = true">{{ t('views.mail.sections.emailSettings.changePasswordButtonLabel') }}</primary-button>
          </template>
          <template v-else>
            <primary-button @click="showPasswordForm = true">{{ t('views.mail.sections.emailSettings.createPasswordButtonLabel') }}</primary-button>
          </template>
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

    form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .set-password-buttons-container {
      display: flex;
      justify-content: flex-end;
      gap: 1rem;
    }

    .success-message {
      margin-block-end: 1rem;
    }
  }

  .display-name-content {
    display: flex;
    align-items: center;
    justify-content: space-between;

    form {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1rem;
      width: 100%;

      .set-display-name-buttons-container {
        display: flex;
        gap: 1rem;
      }
    }
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
    grid-template-columns: 1fr 1fr;
  }
}
</style>