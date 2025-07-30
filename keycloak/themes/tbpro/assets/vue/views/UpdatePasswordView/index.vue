<script setup>
import { TextInput, PrimaryButton, CheckboxInput, NoticeBar } from "@thunderbirdops/services-ui";

</script>

<script>
export default {
  name: 'UpdatePasswordView'
}
</script>


<template>
  <div class="panel">
    <h2>{{ $t('emailForgotTitle') }}</h2>
    <form id="kc-reset-password-form" ref="resetPasswordForm" method="POST" :action="formAction" @submit.prevent="onSubmit" @keyup.enter="onSubmit">
      <notice-bar type="error" v-if="usernameError">{{ $t('forgotPasswordError') }}</notice-bar>
      <div class="form-elements">
        <text-input id="username" name="username" required autocomplete="username" autofocus v-model="username" :help="$t('emailInstruction')" :error="usernameError">{{ $t('email') }}</text-input>
      </div>
      <div class="buttons">
        <primary-button class="submit" @click="onSubmit">{{ $t('doSubmit') }}</primary-button>
      </div>
    </form>
    <template v-if="loginUrl">
      <a :href="loginUrl">{{ $t('backToLogin') }}</a>
    </template>
  </div>
</template>

<style scoped>

</style>