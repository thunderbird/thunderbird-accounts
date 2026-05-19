<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NoticeBar,
  NoticeBarTypes,
  PrimaryButton,
  TextInput,
  LinkButton,
} from '@thunderbirdops/services-ui';
import { setDisplayName } from '../api';

const { t } = useI18n();

const showDisplayNameForm = ref(false);
const displayName = ref<string>(null);
const errorMessageDisplayName = ref(window._page?.formError || '');
const isSubmittingDisplayName = ref(false);
const userDisplayName = ref(window._page?.userDisplayName || '');

// From Stalwart, primary email is always the first email address in the list
const primaryEmail = computed(() => window._page?.emailAddresses?.[0] || '');

const onSetDisplayNameSubmit = async () => {
  if (isSubmittingDisplayName.value) return;

  errorMessageDisplayName.value = '';
  isSubmittingDisplayName.value = true;

  try {
    const data = await setDisplayName(displayName.value);

    if (data.success) {
      userDisplayName.value = displayName.value;
      window._page.userDisplayName = displayName.value;

      // Reset form and close
      displayName.value = '';
      showDisplayNameForm.value = false;
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

const onCancelSetDisplayName = () => {
  errorMessageDisplayName.value = '';
  displayName.value = '';
  showDisplayNameForm.value = false;
};
</script>

<template>
  <div class="user-info-side-container">
    <div>
      <strong>{{ t('views.mail.sections.emailSettings.primaryEmail') }}:</strong>
      <p>{{ primaryEmail }}</p>
    </div>

    <div class="display-name-content">
      <template v-if="showDisplayNameForm">
        <form @submit.prevent="onSetDisplayNameSubmit">
          <text-input v-model="displayName" name="display-name" data-testid="display-name-input">
            {{ t('views.mail.sections.emailSettings.newDisplayName') }}:
          </text-input>

          <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessageDisplayName">{{ errorMessageDisplayName }}</notice-bar>

          <div class="set-display-name-buttons-container">
            <primary-button type="button" variant="outline" @click="onCancelSetDisplayName" :disabled="isSubmittingDisplayName">{{ t('views.mail.sections.emailSettings.cancel') }}</primary-button>
            <primary-button type="button" @click="onSetDisplayNameSubmit" :disabled="isSubmittingDisplayName" data-testid="display-name-set-btn">
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
  </div>
</template>

<style scoped>
.user-info-side-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;

  strong {
    display: block;
    font-weight: 600;
    margin-block-end: 0.25rem;
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
</style>
