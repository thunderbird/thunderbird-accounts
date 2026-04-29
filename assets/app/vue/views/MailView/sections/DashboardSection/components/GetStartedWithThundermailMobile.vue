<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhDownloadSimple, PhQrCode, PhLifebuoy, PhArrowRight } from '@phosphor-icons/vue';
import encodeQR from 'qr';
import { PrimaryButton, LinkButton } from '@thunderbirdops/services-ui';
import {
  encodeAccounts,
  INCOMING_PROTOCOL,
  CONNECTION_SECURITY,
  AUTHENTICATION_TYPE,
} from 'thunderbird-account-qr-code';
import { DOWNLOAD_THUNDERBIRD_MOBILE_URL, IOS_SUPPORT_URL } from '@/defines';
import { FeatureFlag, FeatureFlagValue } from '@/types';
import { isFeatureFlagEnabled } from '@/utils';
import ActionCard from '@/components/ActionCard.vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

const { t } = useI18n();

const isPhaseTwo = isFeatureFlagEnabled(FeatureFlag.PHASE, FeatureFlagValue.PHASE_TWO);

const primaryEmail = computed(() => window._page?.emailAddresses?.[0] || '');
const connectionInfo = computed(() => window._page?.connectionInfo);
const userDisplayName = computed(() => window._page?.userDisplayName || primaryEmail.value);

const qrInput = computed(() => encodeAccounts([{
  incomingProtocol: INCOMING_PROTOCOL.IMAP,
  incomingHostname: connectionInfo.value.IMAP.HOST,
  incomingPort: connectionInfo.value.IMAP.PORT,
  incomingConnectionSecurity: connectionInfo.value.IMAP.TLS ? CONNECTION_SECURITY.Tls : CONNECTION_SECURITY.Plain,
  incomingAuthenticationType: AUTHENTICATION_TYPE.OAuth2,
  incomingUsername: primaryEmail.value,
  outgoingHostname: connectionInfo.value.SMTP.HOST,
  outgoingPort: connectionInfo.value.SMTP.PORT,
  outgoingConnectionSecurity: connectionInfo.value.IMAP.TLS ? CONNECTION_SECURITY.Tls : CONNECTION_SECURITY.Plain,
  outgoingAuthenticationType: AUTHENTICATION_TYPE.OAuth2,
  outgoingUsername: primaryEmail.value,
  identityEmailAddress: primaryEmail.value,
  identityDisplayName: userDisplayName.value,
}]));

const qrCode = computed(() => encodeQR(qrInput.value, 'svg'));
</script>

<script lang="ts">
export default {
  name: 'GetStartedWithThundermailMobile',
};
</script>

<template>
  <div class="action-cards">
    <template v-if="isPhaseTwo">
      <div class="qr-code-container">
        <i18n-t
          keypath="views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.qrCodeDescription"
          class="qr-code-description"
          tag="p"
        >
          <template #thunderbirdForAndroid>
            <strong>
              {{ t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.thunderbirdForAndroid') }}
            </strong>
          </template>
        </i18n-t>
        <details-summary
          :title="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.qrCodeTitle')"
          class="qr-code-details-summary"
        >
          <template #icon>
            <ph-qr-code :size="20" />
          </template>
          <img
            class="qr-code"
            :src="`data:image/svg+xml,${qrCode}`"
            :alt="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.qrCodeAlt')"
          />
        </details-summary>
      </div>
    </template>
    <template v-else>
      <action-card
        :title="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.autoConfigTitle')"
        :description="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.autoConfigDescription')"
      />
    </template>

    <action-card
      :title="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.downloadTitle')"
      :description="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.downloadDescription')"
    >
      <template #icon>
        <ph-download-simple :size="20" />
      </template>
      <template #action>
        <primary-button
          size="small"
          variant="outline"
          :href="DOWNLOAD_THUNDERBIRD_MOBILE_URL"
          target="_blank"
          rel="noopener noreferrer"
          class="download-button"
        >
          {{ t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.downloadButton') }}
        </primary-button>
      </template>
    </action-card>

    <action-card
      :title="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.iosTitle')"
      :description="t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.iosDescription')"
    >
      <template #icon>
        <ph-lifebuoy :size="20" />
      </template>
      <template #action>
        <link-button size="small" :href="IOS_SUPPORT_URL" target="_blank" class="ios-help-button">
          {{ t('views.mail.sections.dashboard.getStartedWithThundermail.mobilePanel.iosSupportButtonLabel') }}

          <template #iconRight>
            <ph-arrow-right :size="16" />
          </template>
        </link-button>
      </template>
    </action-card>
  </div>
</template>

<style scoped>
.action-cards {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;

  .download-button {
    height: 2rem;
  }

  :deep(.ios-help-button) {
    color: var(--colour-primary-pressed);
    padding-inline-end: 0;

    span.text {
      font-size: 0.75rem;
    }
  }

  .qr-code-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem 0.5rem 0.5rem;
    border: 1px solid var(--colour-neutral-border);
    border-radius: 8px;

    .qr-code-details-summary {
      margin-block-end: 0;
    }

    .qr-code-description {
      font-size: 0.75rem;
      color: var(--colour-ti-secondary);
    }
  
    .qr-code {
      width: 150px;
      height: 150px;
      flex-shrink: 0;
    }
  }
}
</style>
