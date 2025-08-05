<script setup>
import { DangerButton, SecondaryButton, NoticeBar } from "@thunderbirdops/services-ui";
import { computed, ref } from "vue";

const message = ref(window._page.message);
const formAction = ref(window._page.currentView?.formAction);
const loginForm = ref();

const deleteCredentialTitle = ref(window._page.currentView?.deleteCredentialTitle);
const deleteCredentialMessage = ref(window._page.currentView?.deleteCredentialMessage);

const isCancelSubmit = ref(false);

const onSubmit = () => {
  loginForm?.value?.submit();
};
const onCancel = () => {
  isCancelSubmit.value = true;
  onSubmit();
};

</script>

<script>
export default {
  name: 'DeleteCredentialView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ deleteCredentialTitle }}</h2>
    <form id="kc-form-delete-credentials" ref="loginForm" method="POST" :action="formAction">
      <notice-bar :type="message.type" v-if="message?.type">{{ message.summary }}</notice-bar>
      <p>{{ deleteCredentialMessage }}</p>
      <div class="buttons">
        <input type="hidden" name="cancel-aia" :value="$t('doCancel')" id="kc-decline" v-if="isCancelSubmit"/>
        <danger-button class="submit" @click="onSubmit" name="accept" id="kc-accept" :value="$t('doConfirmDelete')">{{ $t('doConfirmDelete') }}</danger-button>
        <secondary-button class="submit" @click="onCancel">{{ $t('doCancel') }}</secondary-button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.notice-bar {
  margin-bottom: var(--space-12);
}

.panel {
  margin: 30px
}

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;
}
</style>
