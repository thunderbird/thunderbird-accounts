<script setup>
import {TextInput, PrimaryButton, CheckboxInput} from "@thunderbirdops/services-ui";

</script>

<script>
export default {
  name: 'LoginView'
}
</script>

<template>
  <div class="panel">
    <h2>Sign In</h2>
    <div class="form-elements">
    <text-input name="email">Email</text-input>
    <text-input name="password">Password</text-input>
    </div>
    <div class="post-password-container">
      <checkbox-input name="keep-me-signed-in" label="Keep me signed in"></checkbox-input>
      <a href="#">Forgot Password</a>
    </div>
    <primary-button>Sign In</primary-button>
    <p>Don't have a subscription? <a href="#">Subscribe</a></p>
  </div>
</template>

<style scoped>
.panel {
  margin: 30px
}
.form-elements {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.post-password-container {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}
</style>