<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhSliders, PhInfo } from '@phosphor-icons/vue';
import { ToolTip } from '@thunderbirdops/services-ui';
import DetailsSummary from '@/components/DetailsSummary.vue';
import ServerSettingsCard from '@/components/ServerSettingsCard.vue';

const { t } = useI18n();

enum INCOMING_SERVER_TABS {
  IMAP = 'imap',
  JMAP = 'jmap',
}

const connectionInfo = computed(() => window._page?.connectionInfo);

const incomingServerSelectedTab = ref<INCOMING_SERVER_TABS>(INCOMING_SERVER_TABS.IMAP);

const imapServerDetails = {
  protocol: 'IMAP',
  server: `imap.${connectionInfo.value.IMAP.HOST}`,
  port: `${connectionInfo.value.IMAP.PORT}${connectionInfo.value.IMAP.TLS ? ' (SSL/TLS)' : ''}`,
};

const jmapServerDetails = {
  protocol: 'JMAP',
  server: `jmap.${connectionInfo.value.JMAP.HOST}`,
  port: `${connectionInfo.value.JMAP.PORT}${connectionInfo.value.JMAP.TLS ? ' (SSL/TLS)' : ''}`,
}

const smtpServerDetails = {
  protocol: 'SMTP',
  server: `smtp.${connectionInfo.value.SMTP.HOST}`,
  port: `${connectionInfo.value.SMTP.PORT}${connectionInfo.value.SMTP.TLS ? ' (SSL/TLS)' : ''}`,
}

const incomingServerDetails = computed(() => {
  return incomingServerSelectedTab.value === INCOMING_SERVER_TABS.IMAP ? imapServerDetails : jmapServerDetails;
});
</script>

<template>
  <details-summary :title="t('views.mail.sections.dashboard.viewServerSettings')">
    <template #icon>
      <ph-sliders size="24" />
    </template>

    <div class="view-server-settings-content">
      <server-settings-card
        :title="t('views.mail.sections.dashboard.incomingServer')"
        :details="incomingServerDetails"
      >
        <template #icon>
          <img src="@/assets/svg/inbox-icon.svg" alt="Inbox icon" />
        </template>

        <template #tabs>
          <div class="incoming-server-tabs">
            <button
              :class="{ 'active': incomingServerSelectedTab === INCOMING_SERVER_TABS.IMAP }"
              class="incoming-server-tab"
              @click="incomingServerSelectedTab = INCOMING_SERVER_TABS.IMAP"
            >
              {{ t('views.mail.sections.dashboard.imap') }}
            </button>
            <button
              :class="{ 'active': incomingServerSelectedTab === INCOMING_SERVER_TABS.JMAP }"
              class="incoming-server-tab"
              @click="incomingServerSelectedTab = INCOMING_SERVER_TABS.JMAP"
            >
              {{ t('views.mail.sections.dashboard.jmap') }}
            </button>
          </div>
        </template>

        <template #footer>
          <template v-if="incomingServerSelectedTab === INCOMING_SERVER_TABS.IMAP">
            <div class="what-is-container">
              <ph-info size="24" weight="fill" />
              <span>{{ t('views.mail.sections.dashboard.whatIsImap') }}</span>

              <tool-tip :alt="t('views.mail.sections.dashboard.whatIsImap')">
                <i18n-t keypath="views.mail.sections.dashboard.whatIsImapContent" tag="span">
                  <template #supportUrl>
                    <a href="https://support.tb.pro/hc/articles/46108465880467-What-is-IMAP" target="_blank">{{ t('views.mail.sections.dashboard.clickHere') }}</a>
                  </template>
                </i18n-t>
              </tool-tip>
            </div>
          </template>
          <template v-else>
            <div class="what-is-container">
              <ph-info size="24" weight="fill" />
              <span>{{ t('views.mail.sections.dashboard.whatIsJmap') }}</span>

              <tool-tip :alt="t('views.mail.sections.dashboard.whatIsJmap')">
                <i18n-t keypath="views.mail.sections.dashboard.whatIsJmapContent" tag="span">
                  <template #supportUrl>
                    <a href="https://support.tb.pro/hc/articles/46109214513939-What-is-JMAP" target="_blank">{{ t('views.mail.sections.dashboard.clickHere') }}</a>
                  </template>
                </i18n-t>
              </tool-tip>
            </div>
          </template>
        </template>
      </server-settings-card>

      <server-settings-card
        :title="t('views.mail.sections.dashboard.outgoingServer')"
        :details="smtpServerDetails"
      >
        <template #icon>
          <img src="@/assets/svg/outbox-icon.svg" alt="Outgoing icon" />
        </template>

        <template #tabs>
          <div class="incoming-server-tabs">
            <button class="active incoming-server-tab">
              {{ t('views.mail.sections.dashboard.smtp') }}
            </button>
          </div>
        </template>

        <template #footer>
          <div class="what-is-container">
            <ph-info size="24" weight="fill" />
            <span>{{ t('views.mail.sections.dashboard.whatIsSmtp') }}</span>

            <tool-tip :alt="t('views.mail.sections.dashboard.whatIsSmtp')">
              <i18n-t keypath="views.mail.sections.dashboard.whatIsSmtpContent" tag="span">
                <template #supportUrl>
                  <a href="https://support.tb.pro/hc/articles/46106891841043-What-is-SMTP" target="_blank">{{ t('views.mail.sections.dashboard.clickHere') }}</a>
                </template>
              </i18n-t>
            </tool-tip>
          </div>
        </template>
      </server-settings-card>
    </div>
  </details-summary>
</template>

<style scoped>
.view-server-settings-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 1024px) {
  .view-server-settings-content {
    grid-template-columns: 1fr 1fr;
  }
}
</style>