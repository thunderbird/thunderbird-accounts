import { useSessionStorage } from '@vueuse/core';
import { defineStore } from 'pinia';
import { ref } from 'vue';

 
export const useSignUpFlowStore = defineStore('signUpFlow', () => {
  // State
  const isVisible = ref(false);
  const sessionStorageKeyPrefix = 'accounts/signupFlow'

  // Data
  const name = useSessionStorage(`${sessionStorageKeyPrefix}/name`, null);
  const username = useSessionStorage(`${sessionStorageKeyPrefix}/username`, null);
  const timezone = useSessionStorage(`${sessionStorageKeyPrefix}/timezone`, null);
  const lang = useSessionStorage(`${sessionStorageKeyPrefix}/lang`, null);
  // In-memory only!
  const password = ref(null);
  const confirmPassword = ref(null);

  const errors = ref(null);

  /**
   * Submits a user sign up request with values from sessionStorage + in-memory password.
   * 
   * If the function fails, errors will probably be filled out.
   * 
   * @returns boolean: true if the user is signed up, or false if it failed in anyway. 
   */
  const submit = async () => {
    if (password.value !== confirmPassword.value) {
      return false;
    } 

    const response = await fetch('/api/v1/auth/sign-up/', {
      method: 'POST',
      body: JSON.stringify({
        'username': username.value,
        'password': password.value,
        'zoneinfo': timezone.value,
        'lang': lang.value
      }),
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window._page?.csrfToken,
      },
    });
  
    if (response.status === 200) {
      // Force a reset to remove any sensitive information
      $reset();
    }

    return true;
  };

  /**
   * Restore default state
   */
  const $reset = () => {
    name.value = null;
    username.value = null;
    password.value = null;
    confirmPassword.value = null;
    timezone.value = null;
    lang.value = null;
    // Hmm...
    errors.value = null;
  };

  return {
    name, username, password, confirmPassword, timezone, lang, errors, $reset,
  };
});
