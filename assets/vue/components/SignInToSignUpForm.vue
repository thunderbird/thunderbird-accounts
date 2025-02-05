<script setup>

import {NoticeBar, PrimaryButton} from "@thunderbirdops/services-ui";
import {ref} from "vue";
import CsrfToken from "@/components/CsrfToken.vue";

const signInToContinue = ref();
const errorText = ref(null);

const onSubmit = () => {
  signInToContinue.value.submit();
};

</script>

<template>
  <div class="form-container">
    <notice-bar type="error" v-if="errorText">{{ errorText }}</notice-bar>
    <div class="container">
      <form id="sign-in-form" ref="signInToContinue" method="POST">
        <primary-button @click.capture="onSubmit" id="signInBtn">Sign-in to continue</primary-button>
        <csrf-token></csrf-token>
      </form>
    </div>
  </div>
</template>

<style scoped>
.form-container {
  box-sizing: border-box;
  width: 100%;
  display: flex;
  justify-content: center;
}
</style>