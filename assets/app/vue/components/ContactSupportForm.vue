<script setup>
import { ref } from "vue";

const form = ref({
  // userEmail may be injected from the templates/base.html
  email: window._page?.userEmail || '',
  subject: '',
  product: '-',
  type: '-',
  description: '',
  attachments: []
})

const handleSubmit = () => {
  console.log('Submitting form:', form.value)
}

</script>

<template>
  <form @submit.prevent="handleSubmit">
    <!-- Email -->
    <div class="form-group">
      <label for="email" class="form-label">Your email address(*)</label>
      <input
        id="email"
        type="email"
        v-model="form.email"
        required
        class="form-input"
        :aria-invalid="!form.email"
      >
    </div>

    <!-- Subject -->
    <div class="form-group">
      <label for="subject" class="form-label">Subject*</label>
      <input
        id="subject"
        type="text"
        v-model="form.subject"
        required
        class="form-input"
      >
    </div>

    <!-- Product -->
    <div class="form-group">
      <label for="product" class="form-label">Product*</label>
      <select
        id="product"
        v-model="form.product"
        required
        class="form-select"
      >
        <option value="">-</option>
        <option value="thunderbird_assist">Thunderbird Assist</option>
        <option value="thunderbird_appointment">Thunderbird Appointment</option>
        <option value="thunderbird_send">Thunderbird Send</option>
      </select>
    </div>

    <!-- Type of Request -->
    <div class="form-group">
      <label for="type" class="form-label">Type of Request*</label>
      <select
        id="type"
        v-model="form.type"
        required
        class="form-select"
      >
        <option value="">-</option>
        <option value="accounts_login">Accounts & Login</option>
        <option value="feedback_or_feature_request">Provide Feedback or Request Features</option>
        <option value="payments_billing">Payments & Billing</option>
        <option value="not_listed">Not listed</option>
      </select>
    </div>

    <!-- Description -->
    <div class="form-group">
      <label for="description" class="form-label">Description*</label>
      <input
        id="description"
        v-model="form.description"
        type="text"
        class="form-input"
      >
    </div>

    <div class="form-group">
      <button type="submit" class="form-button">Submit</button>
    </div>
  </form>
</template>

<style scoped>
form {
  max-width: 50%;
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.form-input,
.form-select {
  width: 100%;
  padding: 0.5rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.form-button {
  padding: 0.6rem 1.2rem;
  font-size: 1rem;
  cursor: pointer;
}
</style>