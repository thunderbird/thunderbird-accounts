<script setup>
import { TextInput, PrimaryButton, LinkButton } from "@thunderbirdops/services-ui";
import { computed, useTemplateRef } from "vue";
import CancelForm from '@kc/vue/components/CancelForm.vue';
import { submitKeycloakForm } from '@kc/vue/keycloakForm';

const formAction = window._page.currentView?.formAction;
const recoveryCodePrompt = window._page.currentView?.recoveryCodePrompt;
const errors = window._page.currentView?.errors;
const showTryAnotherWay = window._page.currentView?.showTryAnotherWay === 'true';

const loginForm = useTemplateRef('login-form');
const tryAnotherWayForm = useTemplateRef('try-another-way-form');

const onSubmit = () => {
  submitKeycloakForm(loginForm?.value);
};

const onTryAnotherWay = () => {
  tryAnotherWayForm?.value?.cancel();
};

const recoveryError = computed(() => {
  return errors?.recoveryCodeInput !== '' ? errors?.recoveryCodeInput : null;
});
</script>

<script>
export default {
  name: 'LoginRecoveryAuthnCodeView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('authRecoveryCodeHeader') }}</h2>
    <form id="kc-recovery-code-login-form" ref="login-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
          @keyup.enter="onSubmit">
      <div class="form-elements">
        <text-input data-testid="recovery-code-input" id="recoveryCodeInput" name="recoveryCodeInput"
                    autocomplete="off" required autofocus :error="recoveryError">
          {{ recoveryCodePrompt }}
        </text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit" data-testid="submit-btn">{{ $t('doLogIn') }}</primary-button>
      </div>
    </form>

    <div class="try-another-way" v-if="showTryAnotherWay">
      <cancel-form ref="try-another-way-form" :action="formAction" cancel-name="tryAnotherWay" cancel-value="on"/>
      <link-button data-testid="try-another-way-btn" @click="onTryAnotherWay">{{ $t('doTryAnotherWay') }}</link-button>
    </div>
  </div>
</template>

<style scoped>
.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;

  .submit {
    margin-right: 0;
    margin-left: auto;
  }
}

.try-another-way {
  margin-top: var(--space-12);
  display: flex;
  justify-content: center;
}
</style>
