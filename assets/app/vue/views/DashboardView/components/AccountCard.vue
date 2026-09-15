<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { VisualDivider } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import DisplayName from './DisplayName.vue';
import AppPassword from './AppPassword.vue';
import { isWaffleFlagActive } from '@/utils';
import { getMfaMethods, MfaReauthenticationRequiredError } from '@/views/ManageMfaView/api';
import { WAFFLE_FLAG } from '@/types';

const { t } = useI18n();

// From Stalwart, primary email is always the first email address in the list
const primaryEmail = computed(() => window._page?.emailAddresses?.[0] || '');

const appPasswords = ref<string[]>(window._page?.appPasswords || []);

const showMfa = isWaffleFlagActive(WAFFLE_FLAG.MULTI_FACTOR_AUTHENTICATION);
const hasMfa = ref(false);

// Fetch MFA status when the card mounts so it always reflects current state (an SPA
// navigation back from Manage MFA shows fresh status without a full page reload).
onMounted(async () => {
  if (!showMfa) return;
  try {
    const response = await getMfaMethods();
    hasMfa.value = response.methods.authenticatorApp.set;
  } catch (error) {
    // The methods endpoint requires recent step-up only when an authenticator is set,
    // so a reauth challenge here means MFA is enabled — surface "On" without prompting.
    if (error instanceof MfaReauthenticationRequiredError) {
      hasMfa.value = true;
    }
  }
});
</script>

<template>
  <card-container class="my-account-card">
    <h2>{{ t('views.dashboard.accountCard.accountSettings') }}</h2>
    <p class="account-settings-description">{{ t('views.dashboard.accountCard.accountSettingsDescription') }}</p>

    <div class="my-account-card-details">
      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.email') }}</strong>
        <p>{{ primaryEmail }}</p>
      </div>

      <visual-divider />

      <display-name />

      <visual-divider />

      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.password') }}</strong>
        <div class="my-account-card-field-with-link-button">
          <p>*********</p>
          <a class="fake-button-link" href="/reset-password/">{{ t('views.dashboard.accountCard.change') }}</a>
        </div>
      </div>

      <template v-if="showMfa">
        <visual-divider />

        <div class="my-account-card-field with-outline-button">
          <div>
            <strong>{{ t('views.dashboard.accountCard.mfa') }}</strong>
            <p>{{ hasMfa ? t('views.dashboard.accountCard.on') : t('views.dashboard.accountCard.off') }}</p>
          </div>

          <router-link to="/manage-mfa" class="fake-button-link">
            {{ t('views.dashboard.accountCard.manage') }}
          </router-link>
        </div>
      </template>

      <visual-divider />

      <app-password :app-passwords="appPasswords" />
    </div>
  </card-container>
</template>

<style scoped>
.my-account-card {
  min-width: 100%;
  color: var(--colour-ti-secondary);

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 0.25rem;
  }

  p.account-settings-description {
    font-size: 0.875rem;
    line-height: 1.23;
    color: var(--colour-ti-secondary);
    margin-block-end: 1.5rem;
  }

  .my-account-card-details {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;

    .my-account-card-field {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;

      strong {
        font-weight: 600;
      }

      &.with-outline-button {
        flex-direction: row;
        align-items: end;
        justify-content: space-between;
      }

      .my-account-card-field-with-link-button {
        display: flex;
        align-items: center;
        justify-content: space-between;

        button {
          padding: 0;
        }
      }
    }
  }
}

@media (min-width: 1024px) {
  .my-account-card {
    min-width: 568px;
  }
}

.fake-button-link {
  color: var(--colour-service-primary);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: .5rem;
  border: 0;
  border-radius: var(--border-radius);
  font-family: Inter,"sans-serif";
  font-size: var(--txt-input);
  font-weight: 400;
  line-height: 1;
  cursor: pointer;
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
}
</style>
