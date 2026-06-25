<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { VisualDivider, PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import { isWaffleFlagActive } from '@/utils';
import { getMfaMethods, MfaReauthenticationRequiredError } from '@/views/ManageMfaView/api';

const { t } = useI18n();
const router = useRouter();

// The user's username is their primary email address
const username = computed(() => window._page?.username);

const showMfa = isWaffleFlagActive('multi-factor-authentication');
const hasMfa = ref(false);

const goToManageMfa = () => router.push('/manage-mfa');

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
    <h2>{{ t('views.dashboard.accountCard.myAccount') }}</h2>

    <div class="my-account-card-details">
      <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.email') }}</strong>
        <p>{{ username }}</p>
      </div>

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

          <primary-button variant="outline" size="small" @click="goToManageMfa">
            {{ t('views.dashboard.accountCard.manage') }}
          </primary-button>
        </div>
      </template>

      <!-- <visual-divider /> -->

      <!-- TODO: Uncomment when implementing recovery email -->
      <!-- <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.recoveryEmailAddress') }}</strong>
        <div class="my-account-card-field-with-link-button">
          <base-badge :type="BaseBadgeTypes.Set">{{ t('views.dashboard.accountCard.set') }}</base-badge>
          <link-button>{{ t('views.dashboard.accountCard.change') }}</link-button>
        </div>
      </div> -->

      <!-- <visual-divider /> -->

      <!-- TODO: Uncomment when implementing recovery phone number -->
      <!-- <div class="my-account-card-field">
        <strong>{{ t('views.dashboard.accountCard.recoveryPhoneNumber') }}</strong>
        <div class="my-account-card-field-with-link-button">
          <base-badge :type="BaseBadgeTypes.Set">{{ t('views.dashboard.accountCard.set') }}</base-badge>
          <link-button>{{ t('views.dashboard.accountCard.change') }}</link-button>
        </div>
      </div> -->
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
    margin-block-end: 1rem;
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
        align-items: center;
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
