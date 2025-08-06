<script setup>
import {DangerButton, SecondaryButton, NoticeBar} from "@thunderbirdops/services-ui";
import {useTemplateRef} from "vue";
import CancelForm from '@/vue/components/CancelForm.vue';

const message = window._page.message;
const formAction = window._page.currentView?.formAction;
const loginForm = useTemplateRef('login-form');
const cancelForm = useTemplateRef('cancel-form');

const deleteCredentialTitle = window._page.currentView?.deleteCredentialTitle;
const deleteCredentialMessage = window._page.currentView?.deleteCredentialMessage;

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
  <div class="panel">
    <h2>{{ deleteCredentialTitle }}</h2>
    <cancel-form ref="cancel-form" :action="formAction" cancelId="kc-decline" cancelValue="$t('doCancel')" cancelName="cancel-aia"/>
    <form id="kc-form-delete-credentials" ref="loginForm" method="POST" :action="formAction">
      <notice-bar :type="message.type" v-if="message?.type">{{ message.summary }}</notice-bar>
      <p>{{ deleteCredentialMessage }}</p>
      <div class="buttons">
        <danger-button class="submit" @click="onSubmit" name="accept" id="kc-accept" :value="$t('doConfirmDelete')">
          {{ $t('doConfirmDelete') }}
        </danger-button>
        <secondary-button class="submit" @click="onCancel">{{ $t('doCancel') }}</secondary-button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;
}
</style>
