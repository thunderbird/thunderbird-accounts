<script setup lang="ts">

import {NoticeBar, PrimaryButton, SecondaryButton, TextInput} from "@thunderbirdops/services-ui";
import {ref} from "vue";
import CsrfToken from "@/components/CsrfToken.vue";

const newAppPasswordFormRef = ref();
const deleteAppPasswordFormRef = ref();

const csrfTokenVal = ref(window._page.csrfToken);
const appPasswords = ref(window._page.appPasswords);
const errorText = ref(window._page.formError);

/**
 * Simply submit the form, work-around since we use <button> instead of <input type=submit> in services-ui
 */
const onAddAppPassword = () => {
  newAppPasswordFormRef.value.submit();
}

/**
 * Requires a fetch request since buttons do not store their value in forms
 * @param evt
 * @returns {Promise<void>}
 */
const onDeleteAppPassword = async (evt) => {
  const areYouSure = confirm("Are you sure you want to delete this app password?\n\nAny email clients using this will need to be updated.");
  if (!areYouSure) {
    return;
  }

  // Clear any server error messages
  errorText.value = null;

  const passwordLabel = evt.currentTarget.value;

  const response = await fetch('/self-serve/app-passwords/remove', {
    mode: "same-origin",
    credentials: "include",
    method: 'POST',
    body: JSON.stringify({
      password: passwordLabel
    }),
    headers: {
      'X-CSRFToken': csrfTokenVal.value
    },
  });

  const data = await response.json();

  if (!data.success) {
    errorText.value = 'Failed to remove app password';
    return;
  }

  // Recreate the password label list without the one we just deleted
  window._page.appPasswords = window._page.appPasswords.filter(() => !passwordLabel);
  appPasswords.value = window._page.appPasswords;
}
</script>

<template>
  <div class="form-container">
    <notice-bar type="error" v-if="errorText">{{ errorText }}</notice-bar>
    <p data-testid="app-passwords-create-description">Create App Passwords to login to mail clients like Thunderbird! You cannot view the password after creating it, so make sure to save it.</p>
    <div class="container">
      <div>
        <h3>Existing App Passwords</h3>
        <form id="delete-app-password-form" ref="deleteAppPasswordFormRef" method="post" action="/self-serve/app-passwords/remove">
          <ul class="app-passwords" v-if="appPasswords?.length > 0">
            <li class="app-password" v-for="password in appPasswords" :key="password" :data-testid="'app-passwords-existing-password-' + password">{{ password }}
              <secondary-button size="small" :value="password" @click.capture="onDeleteAppPassword" :data-testid="'app-passwords-delete-app-password-btn-' + password" :aria-label="`Delete ${password} app password.`">Delete</secondary-button>
            </li>
          </ul>
          <p v-else>You don't have any App Passwords.</p>
        </form>
      </div>
      <div>
        <h3>Add a new App Password</h3>
        <form id="new-app-password-form" ref="newAppPasswordFormRef" name="addForm" method="post" action="/self-serve/app-passwords/add" v-if="appPasswords?.length === 0">
          <text-input name="name" data-testid="app-passwords-add-name-input">Name</text-input>
          <text-input name="password" data-testid="app-passwords-add-password-input" type="password">Password</text-input>
          <primary-button data-testid="app-passwords-add-btn" @click.capture="onAddAppPassword">Add</primary-button>
          <csrf-token></csrf-token>
        </form>
        <p v-else>You have reached the maximum number of App Passwords you can create.</p>
      </div>
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

#new-app-password-form, .app-passwords {
  padding-left: 1rem;
  width: 100%;
}
</style>
