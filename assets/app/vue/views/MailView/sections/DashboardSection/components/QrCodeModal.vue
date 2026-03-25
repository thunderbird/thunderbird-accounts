<script setup lang="ts">
import { computed, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  encodeAccounts,
  INCOMING_PROTOCOL,
  CONNECTION_SECURITY,
  AUTHENTICATION_TYPE,
} from 'thunderbird-account-qr-code';
import encodeQR from 'qr';

import GenericModal from '@/components/GenericModal.vue';

const { t } = useI18n();

const genericModal = useTemplateRef<InstanceType<typeof GenericModal>>('genericModal');

const primaryEmail = computed(() => window._page?.emailAddresses?.[0] || '');
const connectionInfo = computed(() => window._page?.connectionInfo);
const userDisplayName = computed(() => window._page?.userDisplayName);

const qrInput = computed(() => encodeAccounts([ {
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
} ]));

const qrCode = computed(() => encodeQR(qrInput.value, "svg"));

defineExpose({
  open: () => {
    genericModal.value.open();
  },
});
</script>

<template>
<generic-modal ref="genericModal" :title="t('views.mail.sections.dashboard.qrCodeModal.title')" >
  <p>{{ t('views.mail.sections.dashboard.qrCodeModal.description') }}</p>
  <img :src="`data:image/svg+xml,${qrCode}`" />
</generic-modal>
</template>

<style scoped>
img {
  max-width: 300px;
}
</style>