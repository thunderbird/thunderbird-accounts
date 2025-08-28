<script setup lang="ts">
import { i18n } from "@/../composables/i18n";
import InlineInput from "@/views/DashboardView/components/InlineInput.vue";
import ContentSection from "@/views/DashboardView/components/ContentSection.vue";
import Divider from "@/views/DashboardView/components/Divider.vue";
import ServicesSection from "@/views/DashboardView/components/ServicesSection.vue";
import {Services} from "../../../defines";

const email = window._page.username;
const password = !!window._page.credentials?.password;
const mfa = !!window._page.credentials?.otp;
const recoveryEmail = window._page.userEmail;
const recoveryPhone = !!window._page.credentials?.sms;

// This will eventually come from backend via user entitlements.
// But since we only support these services right now, it's hardcoded.
const subscribedServices = [
  Services.Thundermail,
  Services.Appointment,
  Services.Send
];

/**
 * This is keycloak specific functionality.
 * Generate an app initiated action url (aia url) and send the user to a secure flow to update their credentials
 */
const keycloakChangeClick = ({ value }) => {
  const aiaUrl = new URL(window._page.aiaUrl);
  aiaUrl.searchParams.append('response_type', 'code');
  // Keycloak needs to be setup to allow this url as a redirect url
  aiaUrl.searchParams.append('redirect_uri', window._page.redirectUri);

    switch (value) {
    case i18n.t('dashboard.fields.password'):
      aiaUrl.searchParams.append('kc_action', 'UPDATE_PASSWORD')
      break;
    case i18n.t('dashboard.fields.mfa'):
      aiaUrl.searchParams.append('kc_action', !mfa ? 'CONFIGURE_TOTP' : 'delete_credential')
      break;
    default:
      alert('Not implemented yet :(');
      return;
  }

  window.open(aiaUrl.toString(), '_blank');
}

</script>

<script lang="ts">
export default {
  name: 'DashboardView'
};
</script>

<template>
  <div id="content">
    <section class="content-column">
      <content-section class="content-section">
        <h1>My Account</h1>
        <div class="fields">
          <a href="http://keycloak:8999/realms/tbpro/protocol/openid-connect/auth?response_type=code&client_id=tb-accounts&redirect_uri=http://localhost:8087/oidc/callback/&kc_action=UPDATE_PASSWORD">Test</a>
          <inline-input :value="email" :label="$t('dashboard.fields.email')"></inline-input>
          <divider/>
          <inline-input @click="keycloakChangeClick" :show-change-link="true" :value="password ? '*************' : $t('dashboard.fields.unset')" :label="$t('dashboard.fields.password')"></inline-input>
          <divider/>
          <inline-input @click="keycloakChangeClick" :show-change-link="true" :value="mfa ? $t('dashboard.fields.on') : $t('dashboard.fields.off')" :label="$t('dashboard.fields.mfa')"></inline-input>
          <divider/>
          <inline-input @click="keycloakChangeClick" :show-change-link="true" :value="recoveryEmail"
                        :label="$t('dashboard.fields.recovery-email')"></inline-input>
          <divider/>
          <inline-input @click="keycloakChangeClick" :show-change-link="true" :value="recoveryPhone ? $t('dashboard.fields.on') : $t('dashboard.fields.off')"
                        :label="$t('dashboard.fields.recovery-phone')"></inline-input>
        </div>
      </content-section>
      <content-section class="content-section">
        <h1>Privacy & Data</h1>
        <inline-input label="Email"></inline-input>
      </content-section>
    </section>
    <divider type="vertical"/>
    <section class="content-column">
      <h1>My Services</h1>
      <services-section :subscribed-services="subscribedServices"/>
    </section>
  </div>
</template>

<style scoped>
#content {
  display: flex;
  height: 100%;
  justify-content: center;
  gap: 27px;
}

.content-column {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.content-section {
  width: 568px;
}

.fields {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
