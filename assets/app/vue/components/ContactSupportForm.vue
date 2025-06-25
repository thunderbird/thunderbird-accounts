<script setup>
import { ref } from "vue";
import { NoticeBar } from "@thunderbirdops/services-ui";
import CsrfToken from "@/components/CsrfToken.vue";

const csrfToken = ref(window._page.csrfToken);
const errorText = ref(window._page.formError);
const form = ref({
  email: window._page?.userEmail || '',
  subject: '',
  product: '',
  type: '',
  description: ''
})

const handleSubmit = async () => {
  errorText.value = null

  const { email, subject, product, type, description } = form.value;

  const response = await fetch('/contact/submit', {
    mode: "same-origin",
    credentials: "include",
    method: 'POST',
    body: JSON.stringify({
      email,
      subject,
      product,
      type,
      description,
    }),
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.value
    },
  });

  const data = await response.json();

  if (!data.success) {
    errorText.value = 'Failed to submit contact form';
    return;
  }
}

</script>

<template>
  <form @submit.prevent="handleSubmit" method="post" action="/contact/submit">
    <!-- Email -->
    <div class="form-group">
      <label for="email" class="form-label">Your email address(*)</label>
      <input
        id="email"
        name="email"
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
        name="subject"
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
        name="product"
        v-model="form.product"
        required
        class="form-select"
      >
        <option disabled value="">-</option>
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
        name="type"
        v-model="form.type"
        required
        class="form-select"
      >
        <option disabled value="">-</option>
        <option value="accounts_login">Accounts & Login</option>
        <option value="feedback_or_feature_request">Provide Feedback or Request Features</option>
        <option value="payments_billing">Payments & Billing</option>
        <option value="not_listed">Not listed</option>
      </select>
    </div>

    <!-- Description -->
    <div class="form-group">
      <label for="description" class="form-label">Description*</label>
      <textarea
        id="description"
        name="description"
        v-model="form.description"
        class="form-textarea"
        rows="6"
      ></textarea>
    </div>

    <notice-bar type="error" v-if="errorText" class="error-notice">{{ errorText }}</notice-bar>

    <div class="form-group">
      <button type="submit" class="form-button">Submit</button>
    </div>

    <csrf-token></csrf-token>
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
.form-select,
.form-textarea {
  width: 100%;
  max-width: 100%;
  padding: 0.5rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  display: block;
  resize: vertical;
}

.form-button {
  padding: 0.6rem 1.2rem;
  font-size: 1rem;
  cursor: pointer;
}

.error-notice {
  margin-bottom: 1rem;
}
</style>