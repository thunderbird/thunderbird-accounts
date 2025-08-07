<script setup>
import { PrimaryButton, SecondaryButton } from '@thunderbirdops/services-ui';
import { computed, useTemplateRef } from 'vue';
import CancelForm from '@/vue/components/CancelForm.vue';

const formAction = window._page.currentView?.formAction;
const showForm = computed(() => window._page.appInitiatedAction !== 'false');

const verifyEmailInstruction = window._page.currentView?.verifyEmailInstruction;
const submitText = window._page.currentView?.submitText;

const verifyEmailForm = useTemplateRef('verify-email-form');
const cancelForm = useTemplateRef('cancel-form');

const onSubmit = () => {
  verifyEmailForm?.value?.submit();
};

const onCancel = () => {
  cancelForm?.value?.cancel();
};
</script>

<script>
export default {
  name: 'VerifyEmailView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('emailVerifyTitle') }}</h2>
    <cancel-form ref="cancel-form" :action="formAction" cancelId="cancelBtn" cancelValue="true"
                 cancelName="cancel-aia"/>
    <form id="kc-verify-email-form" ref="verify-email-form" method="POST" :action="formAction"
          @submit.prevent="onSubmit" @keyup.enter="onSubmit" v-if="showForm">
      <p>{{ verifyEmailInstruction }}</p>
      <div class="buttons">
        <primary-button id="submit" class="submit" @click="onSubmit" :value="submitText">{{
            submitText
          }}
        </primary-button>
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
.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;

}
</style>
