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
  ToolTip,
} from '@thunderbirdops/services-ui';
import { PhX, PhInfo } from '@phosphor-icons/vue';
import { APP_PASSWORD_SUPPORT_URL } from '@/defines';
import { useTour, FTUE_STEPS } from '@/composables/useTour';
import TourCard from '@/components/TourCard.vue';

const { t } = useI18n();
const tour = useTour();

const props = defineProps<{
  appPasswords?: string[];
}>();

const accountHasAppPasswords = ref(props.appPasswords.length > 0);
const showPasswordForm = ref(false);
const appPassword = ref<string>(null);
const appPasswordConfirm = ref<string>(null);
const errorMessage = ref<string>(window._page?.formError || null);
const successMessage = ref<string>(null);
const isSubmitting = ref(false);

const userEmail = computed(() => window._page?.userEmail);

const nextStepText = computed(() => {
  return t('views.mail.ftue.nextStep', { step: t('views.mail.ftue.emailAliases') });
})

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

  errorMessage.value = null;
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
  <div id="app-password-container" class="app-password-side-container">
    <tour-card
      v-if="tour.showFTUE.value && tour.currentStep.value === FTUE_STEPS.APP_PASSWORDS"
      :text="t('views.mail.ftue.step2Text')"
      :current-step="tour.currentStep.value"
      :total-steps="FTUE_STEPS.FINAL"
      :subtitle="nextStepText"
      show-back
      @next="tour.next()"
      @back="tour.back()"
      @close="tour.skip()"
    />

    <div class="app-password-set-indicator-container">
      <strong>{{ t('views.mail.sections.emailSettings.appPassword') }}:</strong>
      <template v-if="accountHasAppPasswords">
        <base-badge :type="BaseBadgeTypes.Set">{{ t('views.mail.sections.emailSettings.set') }}</base-badge>
      </template>
      <template v-else>
        <base-badge :type="BaseBadgeTypes.NotSet">{{ t('views.mail.sections.emailSettings.notSet') }}</base-badge>
      </template>
    </div>

    <p>{{ t('views.mail.sections.emailSettings.changePasswordDescription') }}</p>

    <template v-if="accountHasAppPasswords">
      <p>
        {{ t('views.mail.sections.emailSettings.changePasswordDescriptionTwo') }}
        <span class="info-tooltip-trigger">
          <ph-info size="16" />
          <tool-tip :alt="t('views.mail.sections.emailSettings.changePasswordTooltip')">
            <span>{{ t('views.mail.sections.emailSettings.changePasswordTooltip') }}</span>
          </tool-tip>
        </span>
      </p>
    </template>
    <template v-else>
      <p>
        {{ t('views.mail.sections.emailSettings.createPasswordDescriptionTwo') }}
        <span class="info-tooltip-trigger">
          <ph-info size="16" />
          <tool-tip :alt="t('views.mail.sections.emailSettings.createPasswordTooltip')">
            <i18n-t keypath="views.mail.sections.emailSettings.createPasswordTooltip" tag="span">
              <template #supportUrl>
                <a :href="APP_PASSWORD_SUPPORT_URL" target="_blank">{{ t('views.mail.sections.emailSettings.clickHere') }}</a>
              </template>
            </i18n-t>
          </tool-tip>
        </span>
      </p>
    </template>

    <notice-bar :type="NoticeBarTypes.Success" v-if="successMessage" class="success-message">
      {{ successMessage }}
      <template v-slot:cta>
        <button class="close-button" @click="successMessage = null"
          :aria-label="$t('views.mail.sections.emailSettings.close')">
          <ph-x size="24" />
        </button>
      </template>
    </notice-bar>

    <template v-if="showPasswordForm">
      <form ref="appPasswordFormRef" method="post" action="/app-passwords/set">
        <input type="hidden" name="name" :value="userEmail" />

        <text-input v-model="appPassword" name="password" type="password"
          data-testid="app-passwords-add-password-input">
          {{ t('views.mail.sections.emailSettings.newPassword') }}:
        </text-input>

        <text-input v-model="appPasswordConfirm" name="password-confirm" type="password"
          data-testid="app-passwords-add-password-confirm-input">
          {{ t('views.mail.sections.emailSettings.confirmPassword') }}:
        </text-input>

        <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">
          {{ errorMessage }}
          <template v-slot:cta>
            <button class="close-button" @click="errorMessage = null"
              :aria-label="$t('views.mail.sections.emailSettings.close')">
              <ph-x size="24" />
            </button>
          </template>
        </notice-bar>

        <div class="set-password-buttons-container">
          <primary-button @click="onSetPasswordSubmit" :disabled="isSubmitting" data-testid="app-passwords-add-btn">
            {{
              isSubmitting ? t('views.mail.sections.emailSettings.saving') : t('views.mail.sections.emailSettings.save')
            }}
          </primary-button>
          <link-button @click="onCancelSetPassword" :disabled="isSubmitting">{{
            t('views.mail.sections.emailSettings.cancel') }}
          </link-button>
        </div>
      </form>
    </template>
    <template v-else-if="appPasswords.length > 0">
      <primary-button variant="outline" @click="showPasswordForm = true">{{
        t('views.mail.sections.emailSettings.changePasswordButtonLabel')
        }}</primary-button>
    </template>
    <template v-else>
      <primary-button variant="outline" @click="showPasswordForm = true">{{
        t('views.mail.sections.emailSettings.createPasswordButtonLabel')
        }}</primary-button>
    </template>
  </div>
</template>

<style scoped>
.app-password-side-container {
  p {
    display: flex;
    align-items: center;
    gap: 1ch;
    margin-block-end: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);

    svg {
      cursor: pointer;
    }
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

  .info-tooltip-trigger {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: pointer;

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

.close-button {
  background-color: transparent;
  border: 0;
  cursor: pointer;
}
</style>
