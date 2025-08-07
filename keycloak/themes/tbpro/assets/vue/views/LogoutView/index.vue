<script setup>
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { useTemplateRef } from 'vue';
import MessageBar from '@/vue/components/MessageBar.vue';

const formAction = window._page.currentView?.formAction;
const logoutForm = useTemplateRef('logout-form');

const sessionCode = window._page.currentView?.sessionCode;
const clientUrl = window._page.currentView?.clientUrl;
const onSubmit = () => {
  logoutForm?.value?.submit();
};
</script>

<script>
export default {
  name: 'LogoutView'
};
</script>

<template>
  <div class="panel">
    <h2>{{ $t('logoutConfirmTitle') }}</h2>
    <form id="kc-logout-confirm" ref="logout-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
          @keyup.enter="onSubmit">
      <message-bar />
      <p>{{ $t('logoutConfirmHeader') }}</p>
      <div class="buttons">
        <input type="hidden" name="session_code" :value="sessionCode">
        <primary-button name="confirmLogout" id="kc-logout" class="submit" @click="onSubmit">{{
            $t('doLogout')
          }}
        </primary-button>
      </div>
    </form>
    <template v-if="clientUrl">
      <a :href="clientUrl">{{ $t('backToApplication') }}</a>
    </template>
  </div>
</template>

<style scoped>
.buttons {
  margin-top: var(--space-24);
  margin-bottom: var(--space-24);
  width: 100%;
}
</style>
