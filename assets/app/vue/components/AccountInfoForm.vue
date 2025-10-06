<script setup lang="ts">
import { NoticeBar, PrimaryButton, DangerButton } from '@thunderbirdops/services-ui';
import { ref } from 'vue';

const hasAccount = ref(window._page?.hasAccount);
const errorText = ref(null);

// This should be an anchor tag, but we don't have a button anchor in services-ui yet.
const onSetUp = () => {
  window.location = '/sign-up/';
};

// Placeholder for now
const onDeleteAccount = () => {
  const confirm = window.confirm(
    'Are you sure you want to delete your account and all associated information? This includes your email address and emails!'
  );
  if (confirm) {
    window.alert("This doesn't actually do anything yet. Sorry! See github issue #25.");
  }
};
</script>

<template>
  <div class="form-container">
    <notice-bar type="error" v-if="errorText">{{ errorText }}</notice-bar>
    <div v-if="!hasAccount">
      <h3>Email</h3>
      <p data-testid="account-info-no-email-setup-text">
        You have not setup your email address. Click below to get started!
      </p>
      <primary-button data-testid="account-info-email-setup-btn" @click.capture="onSetUp">Set Up</primary-button>
    </div>
    <div>
      <h3>Delete Account</h3>
      <p data-testid="account-info-delete-account-description">
        You can delete your account and all associated information (including your email address, and emails!)
      </p>
      <danger-button data-testid="account-info-delete-account-btn" @click.capture="onDeleteAccount"
        >Delete Account</danger-button
      >
    </div>
  </div>
</template>

<style scoped>
.form-container {
  margin: 1rem;
  box-sizing: border-box;
}

.container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  width: 50%;
}

/* The <li> */
.app-password {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  background-color: var(--colour-neutral-base);
  padding: 0.375rem 0.75rem;
}

.app-passwords:nth-child(even) {
  background-color: var(--colour-neutral-lower);
}

#new-app-password-form,
.app-passwords {
  padding-left: 1rem;
  width: 100%;
}
</style>
