<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, NoticeBarTypes, PrimaryButton, TextInput } from '@thunderbirdops/services-ui';
import { setDisplayName } from '../api';

const { t } = useI18n();

const showDisplayNameForm = ref(false);
const displayName = ref<string>(null);
const errorMessageDisplayName = ref(window._page?.formError || '');
const isSubmittingDisplayName = ref(false);
const userDisplayName = ref(window._page?.userDisplayName || '');

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
      errorMessageDisplayName.value = data.error || t('views.dashboard.accountCard.anErrorOccurred');
    }
  } catch (error) {
    console.error('Error changing display name:', error);
    errorMessageDisplayName.value = t('views.dashboard.accountCard.anErrorOccurredWhileChangingDisplayName');
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
  <div class="display-name-container">
    <template v-if="showDisplayNameForm">
      <form @submit.prevent="onSetDisplayNameSubmit">
        <text-input v-model="displayName" name="display-name" data-testid="display-name-input">
          {{ t('views.dashboard.accountCard.newDisplayName') }}
        </text-input>

        <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessageDisplayName">{{
          errorMessageDisplayName
        }}</notice-bar>

        <div class="set-display-name-buttons-container">
          <primary-button
            variant="outline"
            @click="onCancelSetDisplayName"
            :disabled="isSubmittingDisplayName"
            >{{ t('views.dashboard.accountCard.cancel') }}</primary-button
          >
          <primary-button
            @click="onSetDisplayNameSubmit"
            :disabled="isSubmittingDisplayName"
            data-testid="display-name-set-btn"
          >
            {{
              isSubmittingDisplayName ? t('views.dashboard.accountCard.saving') : t('views.dashboard.accountCard.save')
            }}
          </primary-button>
        </div>
      </form>
    </template>
    <template v-else>
      <div>
        <strong>{{ t('views.dashboard.accountCard.displayName') }}</strong>
        <p>{{ userDisplayName }}</p>
      </div>

      <button type="button" class="fake-button-link" @click="showDisplayNameForm = true">
        {{ t('views.dashboard.accountCard.change') }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.display-name-container {
  display: flex;
  align-items: end;
  justify-content: space-between;

  strong {
    display: block;
    font-weight: 600;
    margin-block-end: 0.25rem;
  }

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

.fake-button-link {
  color: var(--colour-service-primary);
  border: 0;
  font-size: var(--txt-input);
  font-weight: 400;
  line-height: 1;
  cursor: pointer;
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
  background: transparent;
  padding: 0;
  text-decoration: underline;
}
</style>
