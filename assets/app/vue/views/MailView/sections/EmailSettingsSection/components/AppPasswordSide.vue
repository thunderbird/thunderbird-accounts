<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  BaseBadge,
  BaseBadgeTypes,
  NoticeBar,
  NoticeBarTypes,
  LinkButton,
  PrimaryButton,
  TextInput,
} from '@thunderbirdops/services-ui';
import { APP_PASSWORD_SUPPORT_URL } from '@/defines';

const { t } = useI18n();

const props = defineProps<{
  appPasswords?: string[];
}>();

const accountHasAppPasswords = ref(props.appPasswords.length > 0);
const showPasswordForm = ref(false);
const appPassword = ref<string>(null);
const appPasswordConfirm = ref<string>(null);
const errorMessage = ref(window._page?.formError || '');
const successMessage = ref<string>(null);
const isSubmitting = ref(false);

const userEmail = computed(() => window._page?.userEmail);

const resetPasswordForm = () => {
  errorMessage.value = '';
  appPassword.value = null;
  appPasswordConfirm.value = null;
  showPasswordForm.value = false;
}

const onSetPasswordSubmit = async () => {
  if (isSubmitting.value) return;

  if (appPassword.value !== appPasswordConfirm.value) {
    errorMessage.value = t('views.mail.sections.emailSettings.passwordsDoNotMatch');
    return;
  }

  errorMessage.value = '';
  isSubmitting.value = true;

  const label = userEmail.value;

  try {
    const response = await fetch('/app-passwords/set', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window._page.csrfToken,
      },
      body: JSON.stringify({
        name: label,
        password: appPassword.value,
      }),
    });

    const data = await response.json();

    if (data.success) {
      // Reset form and close
      resetPasswordForm();

      successMessage.value = t('views.mail.sections.emailSettings.passwordSetSuccessfully');

      window._page.appPasswords = [...window?._page?.appPasswords ?? [], label];
      accountHasAppPasswords.value = window._page.appPasswords.length > 0;
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

const onCancelSetPassword = () => {
  resetPasswordForm();
};
</script>

<template>
  <div class="app-password-side-container">
    <div class="app-password-set-indicator-container">
      <strong>{{ t('views.mail.sections.emailSettings.appPassword') }}:</strong>
      <template v-if="accountHasAppPasswords">
        <base-badge :type="BaseBadgeTypes.Set">{{ t('views.mail.sections.emailSettings.set') }}</base-badge>
      </template>
      <template v-else>
        <base-badge :type="BaseBadgeTypes.NotSet">{{ t('views.mail.sections.emailSettings.notSet') }}</base-badge>
      </template>
    </div>

    <p>
      <i18n-t keypath="views.mail.sections.emailSettings.changePasswordDescription">
        <template v-slot:supportUrl>
          <a :href="APP_PASSWORD_SUPPORT_URL" data-testid="go-to-app-password-support-url">
            {{ $t('views.mail.sections.emailSettings.appPasswords') }}
          </a>
        </template>
      </i18n-t>
    </p>

    <notice-bar :type="NoticeBarTypes.Success" v-if="successMessage" class="success-message">{{
      successMessage
    }}</notice-bar>

    <template v-if="showPasswordForm">
      <form ref="appPasswordFormRef" method="post" action="/app-passwords/set">
        <input type="hidden" name="name" :value="userEmail" />

        <text-input
          v-model="appPassword"
          name="password"
          type="password"
          data-testid="app-passwords-add-password-input"
        >
          {{ t('views.mail.sections.emailSettings.newPassword') }}:
        </text-input>

        <text-input
          v-model="appPasswordConfirm"
          name="password-confirm"
          type="password"
          data-testid="app-passwords-add-password-confirm-input"
        >
          {{ t('views.mail.sections.emailSettings.confirmPassword') }}:
        </text-input>

        <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">{{ errorMessage }}</notice-bar>

        <div class="set-password-buttons-container">
          <primary-button @click="onSetPasswordSubmit" :disabled="isSubmitting" data-testid="app-passwords-add-btn">
            {{
              isSubmitting ? t('views.mail.sections.emailSettings.saving') : t('views.mail.sections.emailSettings.save')
            }}
          </primary-button>
          <link-button variant="outline" @click="onCancelSetPassword" :disabled="isSubmitting"
            >{{ t('views.mail.sections.emailSettings.cancel') }}
          </link-button>
        </div>
      </form>
      <p>{{ t('views.mail.sections.emailSettings.changePasswordDescriptionTwo') }}</p>
    </template>
    <template v-else-if="appPasswords.length > 0">
      <primary-button variant="outline" @click="showPasswordForm = true">{{
        t('views.mail.sections.emailSettings.changePasswordButtonLabel')
      }}</primary-button>
    </template>
    <template v-else>
      <primary-button @click="showPasswordForm = true">{{
        t('views.mail.sections.emailSettings.createPasswordButtonLabel')
      }}</primary-button>
    </template>
  </div>
</template>

<style scoped>
.app-password-side-container {
  p {
    margin-block-end: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  strong {
    display: block;
    font-weight: 600;
    margin-block-end: 0.25rem;
  }

  .set-password-buttons-container {
    display: flex;
    justify-content: flex-start;
    gap: 1rem;
  }

  .app-password-set-indicator-container {
    margin-bottom: 1rem;
  }

  .success-message {
    margin-block-end: 1rem;
  }
}
</style>
