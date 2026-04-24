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

  const errorMessage = ref<string|null>(null);

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

    const response = await fetch('/api/v1/auth/sign-up/', {
      method: 'POST',
      body: JSON.stringify({
        'email': verificationEmail.value,
        'partialUsername': username.value,
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
      $reset(false);
      return true;
    } else if (response.status === 429) { // Throttled by rate limiter
      errorMessage.value = (await response.json())?.detail ?? null;
      console.log(errorMessage.value);
      return false;
    }  

    // Server errors
    try {
      const error = (await response.json()) ?? null;
      if (!error) {
        return false;
      }
      errorMessage.value = error['error'] ?? 'Unknown Error';

      const type: string = error['type'] ?? 'unknown-error';
      if (type === 'go-to-wait-list') {
        // Don't show this error, just redirect!
        errorMessage.value = null;
        window.location.href = error['href'];
        return false;
      }

      // What step are we moving the user back to?
      if (type.indexOf('invalidPassword') === 0) {
        step.value = SignUpSteps.PASSWORD;
      } else if (type === 'status-409') { // User already exists error (this comes from keycloak)
        step.value = SignUpSteps.VERIFY;
      } else {
        step.value = SignUpSteps.USERNAME;
      }
    } catch {
      errorMessage.value = 'Unknown error';
    }
    return false;
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
        return;
    }
    step.value = nextStepValue;
  }

  /**
   * Restore default state
   * By default we also reset the current step, but this behaviour can be disabled with the resetStep param.
   */
  const $reset = (resetStep: boolean = true) => {
    name.value = null;
    username.value = null;
    verificationEmail.value = null;
    password.value = null;
    confirmPassword.value = null;
    timezone.value = null;
    lang.value = null;
    errorMessage.value = null;
    if (resetStep) {
      step.value = SignUpSteps.USERNAME;
    }
  };

  return {
    name, username, password, confirmPassword, timezone, lang, errorMessage, step, nextStep, fullUsername, verificationEmail, submit, $reset,
  };
});
