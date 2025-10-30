<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes, PrimaryButton, TextInput } from '@thunderbirdops/services-ui';

const { t } = useI18n();

defineProps<{
  appPasswords?: string[];
}>();

const showPasswordForm = ref(false);
const appPassword = ref<string>(null);
const appPasswordConfirm = ref<string>(null);
const errorMessage = ref(window._page?.formError || '');
const successMessage = ref<string>(null);
const isSubmitting = ref(false);

const userEmail = computed(() => window._page?.userEmail);

const onSetPasswordSubmit = async () => {
  if (isSubmitting.value) return;

  if (appPassword.value !== appPasswordConfirm.value) {
    errorMessage.value = t('views.mail.sections.emailSettings.passwordsDoNotMatch');
    return;
  }

  errorMessage.value = '';
  isSubmitting.value = true;

  try {
    const response = await fetch('/app-passwords/set', {
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

const onCancelSetPassword = () => {
  errorMessage.value = '';
  appPassword.value = '';
  showPasswordForm.value = false;
};
</script>

<template>
  <div class="app-password-side-container">
    <p>{{ t('views.mail.sections.emailSettings.changePasswordDescription') }}</p>
    <p>{{ t('views.mail.sections.emailSettings.changePasswordDescriptionTwo') }}</p>

    <notice-bar :type="NoticeBarTypes.Success" v-if="successMessage" class="success-message">{{ successMessage }}</notice-bar>

    <template v-if="showPasswordForm">
      <form
        ref="appPasswordFormRef"
        method="post"
        action="/app-passwords/set"
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
</style>