<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { KEYCLOAK_URL } from '@/defines';
import { MaintenanceNotice } from '@/types';

// Same messages and rules as the login page (keycloak/themes/tbpro/assets/vue/views/LoginView/index.vue).
const LOGIN_MESSAGES_URL = `${KEYCLOAK_URL}/resources/tbpro/login/en`;

const notice = ref<MaintenanceNotice | null>(null);

// The status URL is operator-entered, so only http(s) links are rendered (never javascript: and the like).
const httpUrlOrNull = (value?: string) => {
  try {
    const url = new URL(value?.trim() ?? '');
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
};

onMounted(async () => {
  try {
    const response = await fetch(LOGIN_MESSAGES_URL);
    const entries: { key: string; value: string }[] = await response.json();
    const messages = Object.fromEntries(entries.map(({ key, value }) => [key, value]));
    const text = messages.maintenanceNotice?.trim();
    if (!text) return;

    notice.value = {
      text,
      type:
        [NoticeBarTypes.Info, NoticeBarTypes.Warning, NoticeBarTypes.Critical].find(
          (type) => type === messages.maintenanceNoticeType
        ) ?? NoticeBarTypes.Warning,
      statusUrl: httpUrlOrNull(messages.maintenanceNoticeStatusUrl),
      statusText: messages.maintenanceNoticeStatusText?.trim() || null,
    };
  } catch {
    // Keycloak unreachable, or an error page instead of the message list: show no notice.
  }
});
</script>

<template>
  <notice-bar
    v-if="notice"
    :type="notice.type"
    class="maintenance-notice"
    role="status"
    data-testid="maintenance-notice"
  >
    {{ notice.text }}
    <a
      v-if="notice.statusUrl && notice.statusText"
      :href="notice.statusUrl"
      target="_blank"
      rel="noopener"
      data-testid="maintenance-notice-status-url"
      >{{ notice.statusText }}</a
    >
  </notice-bar>
</template>

<style scoped>
.maintenance-notice {
  /* A pasted status URL must wrap instead of widening the page past a phone screen. */
  overflow-wrap: anywhere;
}
</style>
