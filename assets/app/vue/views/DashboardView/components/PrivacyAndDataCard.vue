<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import { signOutAllSessions } from '@/views/MailView/views/SecuritySettingsView/api';

const { t } = useI18n();
const router = useRouter();

const goToActiveSessions = () => router.push('/mail/security-settings');
const goToContact = () => router.push('/contact');
const logoutFromAllSessions = () => signOutAllSessions();
</script>

<template>
  <card-container class="privacy-and-data-card">
    <h2>{{ t('views.dashboard.privacyAndDataCard.privacyAndData') }}</h2>

    <div class="privacy-and-data-card-details">
      <div>
        <strong>{{ t('views.dashboard.privacyAndDataCard.activeSessions') }}</strong>
        <p>{{ t('views.dashboard.privacyAndDataCard.activeSessionsText') }}</p>
    
        <div class="active-sessions-actions">
          <primary-button variant="outline" size="small" class="manage-active-sessions-button" @click="goToActiveSessions">
            {{ t('views.dashboard.privacyAndDataCard.manageActiveSessionsButtonLabel') }}
          </primary-button>

          <div class="link-text">
            <a href="/logout/" @click.prevent="logoutFromAllSessions">
              {{ t('views.dashboard.privacyAndDataCard.logoutFromAllSessionsLink') }}
            </a>
          </div>
        </div>
      </div>
  
      <div class="divider"></div>
  
      <div>
        <strong>{{ t('views.dashboard.privacyAndDataCard.deleteAccount') }}</strong>
        <p>{{ t('views.dashboard.privacyAndDataCard.deleteAccountText') }}</p>

        <primary-button variant="outline" size="small" class="delete-account-button" @click="goToContact">
          {{ t('views.dashboard.privacyAndDataCard.deleteAccountButtonLabel') }}
        </primary-button>
      </div>
    </div>
  </card-container>
</template>

<style scoped>
.privacy-and-data-card {
  min-width: unset;
  color: var(--colour-ti-secondary);

  .privacy-and-data-card-details {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 1rem;
  }

  strong {
    display: block;
    font-weight: 600;
    letter-spacing: 0.48px;
    margin-block-end: 0.5rem;
  }

  p {
    margin-block-end: 1rem;
    line-height: 1.32;
  }

  .active-sessions-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .link-text {
    display: flex;
    align-items: center;
    min-height: 2.75rem;

    a {
      width: auto;
      height: 0.938rem;
      flex-grow: 0;
      font-family: Inter;
      font-size: 0.75rem;
      font-weight: normal;
      font-stretch: normal;
      font-style: normal;
      line-height: normal;
      letter-spacing: normal;
      text-align: left;
      color: var(--text-icon-highlight);
      white-space: nowrap;
    }
  }

  .divider {
    width: 100%;
    height: 1px;
    background-color: var(--colour-neutral-border);
  }

  .manage-active-sessions-button {
    --button-outline-border: linear-gradient(to bottom, #58c9ff 131%, var(--text-icons-highlight-blue) 85%, #175fb6 -8%);
    width: 12.125rem;
    height: 2.75rem;
    flex-grow: 0;
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    gap: 8px;
    padding: 1.125rem 1rem;
    border-radius: 8px;
    background-color: var(--neutral-0);
    white-space: nowrap;
  }

  .delete-account-button {
    --button-outline-border: var(--critical-default);
    width: 13.625rem;
    height: 2.75rem;
    flex-grow: 0;
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    gap: 8px;
    padding: 1.125rem 1rem;
    border-radius: 8px;
    border: solid 1px var(--critical-default);
    background-color: var(--surface-base);
  }
}

@media (min-width: 1024px) {
  .privacy-and-data-card {
    min-width: 568px;
  }
}
</style>
