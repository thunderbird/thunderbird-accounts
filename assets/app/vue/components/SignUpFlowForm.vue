<script setup lang="ts">

import {NoticeBar, PrimaryButton, SecondaryButton, SelectInput, TextInput} from "@thunderbirdops/services-ui";
import {ref} from "vue";
import CsrfToken from "@/components/CsrfToken.vue";

const signUpFlow = ref();
const errorText = ref(window._page.formError);
const userLoginEmail = ref(window._page.userEmail);
const cancelRedirect = window._page.cancelRedirect;

const availableDomains = window._page.allowedDomains.map((val) => {
  return {
    label: val,
    value: val,
  }
});
const selectedDomain = ref(availableDomains[0]?.value ?? null);

const onSubmit = () => {
  signUpFlow.value.submit();
}

// This should be an anchor tag, but we don't have a button anchor in services-ui yet.
const onCancel = () => {
  window.location = cancelRedirect;
};
</script>

<template>
  <div class="form-container">
    <notice-bar type="error" v-if="errorText">{{ errorText }}</notice-bar>
    <div class="container">
      <p data-testid="sign-up-description-text">Thank you for your interest in signing up. Please enter a desired email address, and select a domain below.</p>
      <form id="sign-up-flow-form" ref="signUpFlow" method="POST" action="/sign-up/submit">
        <div class="split-input">
          <text-input name="email_address" required="required" data-testid="sign-up-email-address-input">Email Address</text-input>
          <select-input name="email_domain" :options="availableDomains" :model-value="selectedDomain" required="required" data-testid="sign-up-domain-input">Domain</select-input>
        </div>
        <text-input :model-value="userLoginEmail" disabled="disabled" help="You'll use this email to login via Mozilla Accounts to our self-serve page and to your mail client" data-testid="sign-up-login-username-input">Login Username / Email</text-input>
        <text-input name="app_password" required="required" type="password" help="You'll use this password sign-in to your mail client" data-testid="sign-up-app-password-input">App Password</text-input>
        <br/>
        <div class="button-container">
          <primary-button @click.capture="onSubmit" id="sign-up-btn" data-testid="sign-up-sign-up-btn"
            >Sign Up</primary-button
          >
          <secondary-button @click.capture="onCancel" id="cancel-btn" data-testid="sign-up-cancel-btn"
            >Cancel</secondary-button
          >
        </div>
        <csrf-token></csrf-token>
      </form>
    </div>
  </div>
</template>

<style scoped>
.form-container {
  box-sizing: border-box;
  width: 100%;
}

#sign-up-flow-form {
  width: 50%;
}

.split-input {
  display: flex;
  gap: 0.25rem;
  align-items: center;

  &:deep(.wrapper) {
    width: 50%;
  }
}

/* Bug fix for tbpro inputs */
:deep(.tbpro-input) {
  box-sizing: border-box;
}

.button-container {
  display: flex;
  flex-direction: row;
  gap: 1rem;
}
</style>
