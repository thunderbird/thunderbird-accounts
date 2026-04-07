<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhInfo } from '@phosphor-icons/vue';
import { ToolTip } from '@thunderbirdops/services-ui';
import ServerSettingsCardItem from '@/components/ServerSettingsCardItem.vue';
import { WHAT_IS_IMAP_SUPPORT_URL, WHAT_IS_JMAP_SUPPORT_URL, WHAT_IS_SMTP_SUPPORT_URL } from '@/defines';

defineProps<{
  isManualConfigurationSection?: boolean;
}>();

const { t } = useI18n();

enum INCOMING_SERVER_TABS {
  IMAP = 'imap',
  JMAP = 'jmap',
}

const connectionInfo = computed(() => window._page?.connectionInfo);

const incomingServerSelectedTab = ref<INCOMING_SERVER_TABS>(INCOMING_SERVER_TABS.IMAP);

const imapServerDetails = computed(() => ({
  protocol: 'IMAP',
  server: `imap.${connectionInfo.value.IMAP.HOST}`,
  port: `${connectionInfo.value.IMAP.PORT}${connectionInfo.value.IMAP.TLS ? ' (SSL/TLS)' : ''}`,
}));

const jmapServerDetails = computed(() => ({
  protocol: 'JMAP',
  server: `jmap.${connectionInfo.value.JMAP.HOST}`,
  port: `${connectionInfo.value.JMAP.PORT}${connectionInfo.value.JMAP.TLS ? ' (SSL/TLS)' : ''}`,
}));

const smtpServerDetails = computed(() => ({
  protocol: 'SMTP',
  server: `smtp.${connectionInfo.value.SMTP.HOST}`,
  port: `${connectionInfo.value.SMTP.PORT}${connectionInfo.value.SMTP.TLS ? ' (SSL/TLS)' : ''}`,
}));

const incomingServerDetails = computed(() =>
  incomingServerSelectedTab.value === INCOMING_SERVER_TABS.IMAP
    ? imapServerDetails.value
    : jmapServerDetails.value,
);
</script>

<template>
  <div>
    <div v-if="isManualConfigurationSection" class="inner-spacing" />

    <div
      class="view-server-settings-content"
      :class="{ 'spacing-small': isManualConfigurationSection }"
    >
      <server-settings-card-item
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
                    <a :href="WHAT_IS_IMAP_SUPPORT_URL" target="_blank">{{ t('views.mail.sections.dashboard.clickHere') }}</a>
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
                    <a :href="WHAT_IS_JMAP_SUPPORT_URL" target="_blank">{{ t('views.mail.sections.dashboard.clickHere') }}</a>
                  </template>
                </i18n-t>
              </tool-tip>
            </div>
          </template>
        </template>
      </server-settings-card-item>
  
      <server-settings-card-item
        :title="t('views.mail.sections.dashboard.outgoingServer')"
        :details="smtpServerDetails"
      >
        <template #icon>
          <img src="@/assets/svg/outbox-icon.svg" alt="Outgoing icon" />
        </template>
  
        <template #tabs>
          <div class="incoming-server-tabs">
            <button class="active incoming-server-tab" type="button">
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
                  <a :href="WHAT_IS_SMTP_SUPPORT_URL" target="_blank">{{ t('views.mail.sections.dashboard.clickHere') }}</a>
                </template>
              </i18n-t>
            </tool-tip>
          </div>
        </template>
      </server-settings-card-item>
    </div>
  </div>
</template>

<style scoped>
.view-server-settings-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;

  &.spacing-small {
    gap: 0.5rem;
  }
}

.inner-spacing {
  margin-block-end: 0.25rem;
}

@media (min-width: 1024px) {
  .view-server-settings-content {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
