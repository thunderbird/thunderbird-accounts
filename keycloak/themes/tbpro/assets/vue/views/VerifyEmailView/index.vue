<script setup>
import { TextInput, PrimaryButton, SecondaryButton, NoticeBar } from "@thunderbirdops/services-ui";
import { ref, computed } from "vue";

const errors = ref(window._page.currentView?.errors);
const formAction = ref(window._page.currentView?.formAction);
const showForm = computed(() => window._page.appInitiatedAction !== '');

const verifyEmailInstruction = ref(window._page.currentView?.verifyEmailInstruction);
const submitText = ref(window._page.currentView?.submitText);
const isCancelSubmit = ref(false);

const verifyEmailForm = ref();

const onSubmit = () => {
  console.log("submitting with ", verifyEmailForm.value);
  verifyEmailForm?.value?.submit();
};

const onCancel = () => {
  isCancelSubmit.value = true;
  onSubmit();
}
</script>

<script>
export default {
  name: 'VerifyEmailView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('emailVerifyTitle') }}</h2>
    <form id="kc-verify-email-form" ref="verifyEmailForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit" v-if="showForm">
      <p>{{ verifyEmailInstruction }}</p>
      <div class="buttons">
        <input v-if="isCancelSubmit" type="hidden" name="cancel-aia" value="true"/>
        <primary-button id="submit" class="submit" @click="onSubmit" :value="submitText">{{ submitText }}</primary-button>
        <secondary-button id="cancel" class="submit" @click="onCancel">{{ $t('doCancel') }}</secondary-button>
      </div>
    </form>
    <template v-else>
      <a :href="formAction">{{ $t('doClickHere') }}</a>
      {{ $t('emailVerifyInstruction3') }}
    </template>
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