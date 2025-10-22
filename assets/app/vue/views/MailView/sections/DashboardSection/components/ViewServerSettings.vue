<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhSliders, PhGlobe, PhCopySimple, PhKey, PhInfo } from '@phosphor-icons/vue';
import DetailsSummary from '@/components/DetailsSummary.vue';

const { t } = useI18n();

enum INCOMING_SERVER_TABS {
  IMAP = 'imap',
  JMAP = 'jmap',
}

const incomingServerSelectedTab = ref<INCOMING_SERVER_TABS>(INCOMING_SERVER_TABS.IMAP);

const imapServerDetails = {
  protocol: 'IMAP',
  hostname: 'imap.thundermail.com',
  domain: 'thundermail.com',
  port: 993,
  authentication: 'SSL/TLS',
};

const jmapServerDetails = {
  protocol: 'JMAP',
  hostname: 'jmap.thundermail.com',
  domain: 'thundermail.com',
  port: 443,
  authentication: 'SSL/TLS',
}

const smtpServerDetails = {
  protocol: 'SMTP',
  hostname: 'smtp.thundermail.com',
  domain: 'thundermail.com',
  port: 993,
  authentication: 'SSL/TLS',
}

const incomingServerDetails = computed(() => {
  return incomingServerSelectedTab.value === INCOMING_SERVER_TABS.IMAP ? imapServerDetails : jmapServerDetails;
});

const copyValue = async (value: string | number) => {
  try {
    await navigator.clipboard.writeText(String(value));
  } catch (_err) {
    // noop
  }
};
</script>

<template>
  <details-summary
    :title="t('views.mail.sections.dashboard.viewServerSettings')"
    :default-open="true"
  >
    <template #icon>
      <ph-sliders size="24" />
    </template>

    <div class="view-server-settings-content">
      <div>
        <header>{{ t('views.mail.sections.dashboard.incomingServer') }}</header>
        
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

        <div class="server-detail-item">
          <ph-globe size="20" />
          <strong>{{ t('views.mail.sections.dashboard.protocol') }}</strong>
          <span>{{ incomingServerDetails.protocol }}</span>
          <button type="button" class="copy-btn" @click="copyValue(incomingServerDetails.protocol)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <div class="server-detail-item">
          <ph-globe size="20" />
          <strong>{{ t('views.mail.sections.dashboard.hostname') }}</strong>
          <span>
            {{ incomingServerDetails.hostname.split('.').slice(0, -2).join('.') }}.<strong>{{ incomingServerDetails.domain }}</strong>
          </span>
          <button type="button" class="copy-btn" @click="copyValue(incomingServerDetails.hostname)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <div class="server-detail-item">
          <ph-globe size="20" />
          <strong>{{ t('views.mail.sections.dashboard.port') }}</strong>
          <span>{{ incomingServerDetails.port }}</span>
          <button type="button" class="copy-btn" @click="copyValue(incomingServerDetails.port)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <div class="server-detail-item">
          <ph-key size="20" />
          <strong>{{ t('views.mail.sections.dashboard.authentication') }}</strong>
          <span>{{ incomingServerDetails.authentication }}</span>
          <button type="button" class="copy-btn" @click="copyValue(incomingServerDetails.authentication)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <template v-if="incomingServerSelectedTab === INCOMING_SERVER_TABS.IMAP">
          <router-link class="what-is-link" to="#">
            <ph-info size="24" weight="fill" />
            <span>{{ t('views.mail.sections.dashboard.whatIsImap') }}</span>
          </router-link>
        </template>
        <template v-else>
          <router-link class="what-is-link" to="#">
            <ph-info size="24" weight="fill" />
            <span>{{ t('views.mail.sections.dashboard.whatIsJmap') }}</span>
          </router-link>
        </template>
      </div>

      <div>
        <header>{{ t('views.mail.sections.dashboard.outgoingServer') }}</header>

        <div class="server-detail-item">
          <ph-globe size="20" />
          <strong>{{ t('views.mail.sections.dashboard.protocol') }}</strong>
          <span>{{ smtpServerDetails.protocol }}</span>
          <button type="button" class="copy-btn" @click="copyValue(smtpServerDetails.protocol)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <div class="server-detail-item">
          <ph-globe size="20" />
          <strong>{{ t('views.mail.sections.dashboard.hostname') }}</strong>
          <span>{{ smtpServerDetails.hostname }}</span>
          <button type="button" class="copy-btn" @click="copyValue(smtpServerDetails.hostname)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <div class="server-detail-item">
          <ph-globe size="20" />
          <strong>{{ t('views.mail.sections.dashboard.port') }}</strong>
          <span>{{ smtpServerDetails.port }}</span>
          <button type="button" class="copy-btn" @click="copyValue(smtpServerDetails.port)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <div class="server-detail-item">
          <ph-key size="20" />
          <strong>{{ t('views.mail.sections.dashboard.authentication') }}</strong>
          <span>{{ smtpServerDetails.authentication }}</span>
          <button type="button" class="copy-btn" @click="copyValue(smtpServerDetails.authentication)">
            <ph-copy-simple size="20" />
          </button>
        </div>

        <router-link class="what-is-link" to="#">
          <ph-info size="24" weight="fill" />
          <span>{{ t('views.mail.sections.dashboard.whatIsSmtp') }}</span>
        </router-link>
      </div>
    </div>
  </details-summary>
</template>

<style scoped>
.view-server-settings-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;

  header {
    background-color: #f1f7fa;
    padding-block: 0.75rem;
    text-align: center;
    text-transform: uppercase;
    font-family: metropolis;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--colour-ti-secondary);
    letter-spacing: 0.42px;
  }

  .incoming-server-tabs {
    display: flex;
    flex-direction: row;

    .incoming-server-tab {
      padding-block: 1rem;
      font-size: 0.875rem;
      font-family: Inter;
      color: var(--colour-ti-base);
      width: 100%;
      border: none;
      border-block-end: 2px solid transparent;
      background-color: transparent;
      cursor: pointer;
      
      &.active {
        border-block-end: 2px solid var(--colour-ti-highlight);
      }

      &:not(.active) {
        color: var(--colour-ti-muted);
      }
    }
  }

  .server-detail-item {
    display: grid;
    grid-template-columns: 1.5rem 30% 1fr auto;
    align-items: center;
    padding: 0.625rem 0.5rem;
    color: var(--colour-ti-secondary);
    font-size: 0.75rem;
    border-block-end: 1px solid var(--colour-neutral-border);

    &:last-of-type {
      margin-block-end: 1.25rem;
    }
  }

  .copy-btn {
    background: none;
    border: none;
    padding: 0;
    margin: 0;
    color: inherit;
    cursor: pointer;

    &:hover {
      color: var(--colour-primary-hover);
    }

    &:active {
      color: var(--colour-primary-pressed);
    }
  }

  .what-is-link {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    cursor: pointer;
    text-decoration: none;
    color: var(--colour-ti-base);

    span {
      color: var(--colour-ti-muted);
      font-size: 0.75rem;
    }
  }
}
</style>