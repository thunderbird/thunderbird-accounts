<script setup>
import { PrimaryButton, SecondaryButton } from "@thunderbirdops/services-ui";
import { ref } from "vue";

const formAction = ref(window._page.currentView?.formAction);
const logoutForm = ref();

const sessionCode = ref(window._page.currentView?.sessionCode);
const clientUrl = ref(window._page.currentView?.clientUrl);
const onSubmit = () => {
  logoutForm?.value?.submit();
};
</script>

<script>
export default {
  name: 'LogoutView'
}
</script>

<template>
  <div class="panel">
    <h2>{{ $t('logoutConfirmTitle') }}</h2>
    <form id="kc-logout-confirm" ref="logoutForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <p>{{ $t('logoutConfirmHeader') }}</p>
      <div class="buttons">
        <input type="hidden" name="session_code" :value="sessionCode">
        <primary-button name="confirmLogout" id="kc-logout" class="submit" @click="onSubmit">{{ $t('doLogout') }}</primary-button>
      </div>
    </form>
    <template v-if="clientUrl">
      <a :href="clientUrl">{{ $t('backToApplication') }}</a>
    </template>
  </div>
</template>

<style scoped>
.panel {
  margin: 30px
}

.buttons {
  margin-top: var(--space-24);
  margin-bottom: var(--space-24);
  width: 100%;
}
</style>