<script setup>
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { computed, useTemplateRef } from 'vue';
import ThunderbirdLogoLight from '@kc/svg/thunderbird-pro-light.svg';
import CancelForm from '@kc/vue/components/CancelForm.vue';

const formAction = window._page.currentView?.formAction;
const showForm = computed(() => window._page.appInitiatedAction !== 'false');
const clientUrl = window._page.currentView?.clientUrl;
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
  <a :href="clientUrl" class="logo-link">
    <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
  </a>
  <h2>{{ $t('emailVerifyTitle') }}</h2>
  <cancel-form ref="cancel-form" :action="formAction" cancelId="cancelBtn" cancelValue="true"
                cancelName="cancel-aia"/>
  <form id="kc-verify-email-form" ref="verify-email-form" method="POST" :action="formAction"
        @submit.prevent="onSubmit" @keyup.enter="onSubmit" v-if="showForm">
    <p>{{ verifyEmailInstruction }}</p>
    <div class="buttons">
      <primary-button data-testid="submit-btn" id="submit" class="submit" @click="onSubmit" :value="submitText">{{
          submitText
        }}
      </primary-button>
      <primary-button variant="outline" data-testid="cancel-btn" id="cancel" class="submit" @click="onCancel">{{ $t('doCancel') }}</primary-button>
    </div>
  </form>
  <template v-else>
    <a :href="formAction" data-testid="action-url">{{ $t('doClickHere') }}</a>
    {{ $t('emailVerifyInstruction3') }}
  </template>
</template>

<style scoped>
h2 {
  font-size: 1.5rem;
  font-family: metropolis;
  font-weight: normal;
  line-height: 1.1;
  color: var(--colour-primary-default);
  margin: 0 0 1.5rem 0;
}

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

.buttons {
  margin-top: var(--space-24);
  width: 100%;
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;

}
</style>
