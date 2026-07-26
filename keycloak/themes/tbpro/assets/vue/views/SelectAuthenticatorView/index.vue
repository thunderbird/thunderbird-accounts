<script setup>
const formAction = window._page.currentView?.formAction;

// Surface the authenticator app first; recovery codes are a fallback. Falls back to
// Keycloak's original order for any methods not listed here.
const METHOD_ORDER = ['otp-display-name', 'recovery-authn-codes-display-name'];
const priority = (key) => {
  const index = METHOD_ORDER.indexOf(key);
  return index === -1 ? METHOD_ORDER.length : index;
};
const authenticationSelections = [...(window._page.currentView?.authenticationSelections ?? [])]
  .sort((a, b) => priority(a.key) - priority(b.key));
</script>

<script>
export default {
  name: 'SelectAuthenticatorView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('loginChooseAuthenticator') }}</h2>
    <form method="POST" :action="formAction" class="select-auth-form">
      <button
        v-for="selection in authenticationSelections"
        :key="selection.execId"
        class="select-auth-item"
        type="submit"
        name="authenticationExecution"
        :value="selection.execId"
        :data-testid="`select-auth-${selection.execId}`"
      >
        <span class="select-auth-item__body">
          <span class="select-auth-item__title">{{ selection.displayName }}</span>
          <span class="select-auth-item__help">{{ selection.helpText }}</span>
        </span>
        <svg class="select-auth-item__arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </form>
  </div>
</template>

<style scoped>
.select-auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}

.select-auth-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  padding: 1rem 1.125rem;
  border: 0.0625rem solid var(--colour-neutral-border);
  border-radius: 0.5rem;
  background-color: var(--colour-neutral-base, #ffffff);
  color: var(--colour-ti-base);
  transition: var(--transition, 0.2s ease);
}

.select-auth-item:hover {
  border-color: var(--colour-neutral-border-intense);
}

.select-auth-item__body {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  flex-grow: 1;
}

.select-auth-item__title {
  font-weight: 600;
  font-size: 0.9375rem;
}

.select-auth-item__help {
  font-size: 0.875rem;
  color: var(--colour-ti-secondary);
}

.select-auth-item__arrow {
  flex-shrink: 0;
  color: var(--colour-ti-secondary);
}
</style>
