<script setup>
import { DangerButton, PrimaryButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import CancelForm from '@kc/vue/components/CancelForm.vue';
import MessageBar from '@kc/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@kc/svg/thunderbird-pro-light.svg';

const formAction = window._page.currentView?.formAction;
const loginForm = useTemplateRef('login-form');
const cancelForm = useTemplateRef('cancel-form');

const deleteCredentialTitle = window._page.currentView?.deleteCredentialTitle;
const deleteCredentialMessage = window._page.currentView?.deleteCredentialMessage;
const clientUrl = window._page.currentView?.clientUrl;

const onSubmit = () => {
  loginForm?.value?.submit();
};
const onCancel = () => {
  cancelForm?.value?.cancel();
};

</script>

<script>
export default {
  name: 'DeleteCredentialView'
};
</script>

<template>
  <message-bar/>
  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>
  <h2>{{ deleteCredentialTitle }}</h2>
  <cancel-form ref="cancel-form" :action="formAction" cancelId="kc-decline" cancelValue="$t('doCancel')"
                cancelName="cancel-aia"/>
  <form id="kc-form-delete-credentials" ref="login-form" method="POST" :action="formAction">
    <p>{{ deleteCredentialMessage }}</p>
    <div class="buttons">
      <danger-button class="submit" @click="onSubmit" name="accept" id="kc-accept" :value="$t('doConfirmDelete')" data-testid="submit-btn">
        {{ $t('doConfirmDelete') }}
      </danger-button>
      <primary-button variant="outline" class="submit" @click="onCancel" data-testid="cancel-btn">{{ $t('doCancel') }}</primary-button>
    </div>
  </form>
</template>

<style scoped>
.logo-link {
  display: block;
  text-decoration: none;
  margin-block-end: 2.8125rem;

  .logo {
    height: 36px;
    width: auto;
    transition: opacity 0.2s ease;
  }
}

h2 {
  font-size: 1.5rem;
  font-family: metropolis;
  font-weight: normal;
  line-height: 1.1;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;
}
</style>
