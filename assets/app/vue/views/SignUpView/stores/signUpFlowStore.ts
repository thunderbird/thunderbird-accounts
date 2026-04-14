import { LOGIN_ORIGIN } from '@/defines';
import { useSessionStorage } from '@vueuse/core';
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export const enum SignUpSteps {
  INVALID = 0,
  USERNAME = 10,
  PASSWORD = 20,
  VERIFY = 30,
  DONE = 100,
}
 
export const useSignUpFlowStore = defineStore('signUpFlow', () => {
  const sessionStorageKeyPrefix = 'accounts/signupFlow'

  // Data
  const name = useSessionStorage(`${sessionStorageKeyPrefix}/name`, null);
  const username = useSessionStorage(`${sessionStorageKeyPrefix}/username`, null);
  const verificationEmail = useSessionStorage(`${sessionStorageKeyPrefix}/verificationEmail`, null);
  const timezone = useSessionStorage(`${sessionStorageKeyPrefix}/timezone`, null);
  const lang = useSessionStorage(`${sessionStorageKeyPrefix}/lang`, null);
  // In-memory only!
  const step = ref(SignUpSteps.USERNAME);
  const password = ref(null);
  const confirmPassword = ref(null);

  const errors = ref(null);

  const fullUsername = computed(() => `${username.value}@${window._page.currentView?.tbProPrimaryDomain}`)

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

    const response = await fetch('/users/sign-up/', {
      method: 'POST',
      body: JSON.stringify({
        'email': verificationEmail.value,
        'partial_username': username.value,
        'name': name.value,
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
    } else {
      const data = await response.json();
      console.log(response.status, ' : ', data);
      return false;
    }

    return true;
  };

  /**
  * Proceed to the next step of the sign up flow.
  * 
  * Note: There's no previousStep because we intentionally do not have a back button.
  */
  const nextStep = () => {
    let nextStepValue = SignUpSteps.INVALID;
    switch (step.value) {
      case SignUpSteps.USERNAME:
        nextStepValue = SignUpSteps.PASSWORD;
        break;
      case SignUpSteps.PASSWORD:
        nextStepValue = SignUpSteps.VERIFY;
        break;
      case SignUpSteps.VERIFY:
        nextStepValue = SignUpSteps.DONE;
        break; 
    }
    step.value = nextStepValue;
  }

  /**
   * Restore default state
   */
  const $reset = () => {
    name.value = null;
    username.value = null;
    verificationEmail.value = null;
    password.value = null;
    confirmPassword.value = null;
    timezone.value = null;
    lang.value = null;
    step.value = SignUpSteps.USERNAME;
    // Hmm...
    errors.value = null;
  };

  return {
    name, username, password, confirmPassword, timezone, lang, errors, step, nextStep, fullUsername, verificationEmail, submit, $reset,
  };
});
