<script setup>
import { ref } from "vue";
import { NoticeBar, TextInput, SelectInput, PrimaryButton } from "@thunderbirdops/services-ui";
import CsrfToken from "@/components/CsrfToken.vue";

const csrfToken = ref(window._page.csrfToken);
const errorText = ref(window._page.formError);
const successText = ref('');
const form = ref({
  email: window._page?.userEmail || '',
  subject: '',
  product: '',
  type: '',
  description: '',
  attachments: []
})
const fileInput = ref(null)

// Product options for SelectInput
// These values are important to match the Zendesk ticket custom field type
const productOptions = [
  { label: 'Thunderbird Assist', value: 'thunderbird_assist' },
  { label: 'Thunderbird Appointment', value: 'thunderbird_appointment' },
  { label: 'Thunderbird Send', value: 'thunderbird_send' }
];

// Type options for SelectInput
// These values are important to match the Zendesk ticket custom field type
const typeOptions = [
  { label: 'Accounts & Login', value: 'accounts___login' },
  { label: 'Technical', value: 'technical' },
  { label: 'Provide Feedback or Request Features', value: 'provide_feedback_or_request_features' },
  { label: 'Payments & Billing', value: 'payments___billing' },
  { label: 'Not listed', value: 'not_listed' }
];

const triggerFileSelect = () => {
  fileInput.value?.click()
}

const handleFileSelect = async (event) => {
  const files = event.target.files;
  await uploadFiles(files)
  event.target.value = ''
}

const handleDrop = async (event) => {
  const files = event.dataTransfer.files
  await uploadFiles(files)
}

const uploadFiles = async (files) => {
  for (let file of files) {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/contact/attach_file', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': csrfToken.value
        },
      })

      if (!response.ok) throw new Error('Upload failed')

      const data = await response.json()

      if (data.upload_token) {
        form.value.attachments.push({
          filename: data.filename || file.name,
          token: data.upload_token
        })
      }
    } catch (err) {
      console.error('Upload error:', err)
    }
  }
}

const removeAttachment = (index) => {
  form.value.attachments.splice(index, 1)
}

const resetForm = () => {
  form.value = {
    email: window._page?.userEmail || '',
    subject: '',
    product: '',
    type: '',
    description: '',
    attachments: []
  }
  errorText.value = ''
  successText.value = ''
}

const handleSubmit = async () => {
  errorText.value = ''
  successText.value = ''

  const { email, subject, product, type, description, attachments } = form.value;

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
      attachments,
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

  resetForm()
  successText.value = 'Your support request has been submitted successfully. We will get back to you soon.'
}

</script>

<template>
  <form @submit.prevent="handleSubmit" method="post" action="/contact/submit">
    <!-- Email -->
    <text-input
      name="email"
      type="email"
      v-model="form.email"
      required="required"
      data-testid="contact-email-input"
    >
      Your email address(*)
    </text-input>

    <!-- Subject -->
    <text-input
      name="subject"
      type="text"
      v-model="form.subject"
      required="required"
      data-testid="contact-subject-input"
    >
      Subject*
    </text-input>

    <!-- Product -->
    <select-input
      name="product"
      :options="productOptions"
      v-model="form.product"
      required="required"
      data-testid="contact-product-input"
    >
      Product*
    </select-input>

    <!-- Type of Request -->
    <select-input
      name="type"
      :options="typeOptions"
      v-model="form.type"
      required="required"
      data-testid="contact-type-input"
    >
      Type of Request*
    </select-input>

    <!-- Description -->
    <text-input
      name="description"
      type="textarea"
      v-model="form.description"
      required="required"
      data-testid="contact-description-input"
    >
      Description*
    </text-input>

    <div
      class="form-group file-dropzone"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileSelect"
      role="button"
      aria-label="Upload files"
    >
      <p v-if="form.attachments.length === 0">Drag & drop files here, or click to upload</p>
      <p v-else>{{ form.attachments.length }} file(s) uploaded. Drag & drop more files here, or click to upload</p>
      <input
        type="file"
        ref="fileInput"
        class="hidden"
        multiple
        @change="handleFileSelect"
      >
    </div>

    <ul v-if="form.attachments.length" class="attachment-list">
      <li v-for="(attachment, index) in form.attachments" :key="index">
        <span class="attachment-filename">{{ attachment.filename }}</span>
        <button @click="removeAttachment(index)" class="remove-attachment-btn">Remove</button>
      </li>
    </ul>

    <notice-bar type="error" v-if="errorText" class="notice">{{ errorText }}</notice-bar>
    <notice-bar type="success" v-if="successText" class="notice">{{ successText }}</notice-bar>

    <div class="form-group">
      <primary-button @click.capture="handleSubmit" data-testid="contact-submit-btn">
        Submit
      </primary-button>
    </div>

    <csrf-token></csrf-token>
  </form>
</template>

<style scoped>
form {
  margin-block-start: 1rem;
  max-width: 50%;
}

.form-group {
  margin-block-end: 1rem;
}

/* Bug fix: select-input's labels have a .wrapper class with a max-width of 320px */
.wrapper {
  max-width: 100%;
}

.file-dropzone {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
  cursor: pointer;
  outline: none;
}

.file-dropzone:hover {
  border-color: #888;
}

.file-dropzone:focus {
  border-color: #333;
}

.notice {
  margin-bottom: 1rem;
}

.attachment-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.attachment-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  background-color: #f9f9f9;
}

.attachment-list a {
  color: #0066cc;
  text-decoration: none;
}

.attachment-list a:hover {
  text-decoration: underline;
}

.attachment-filename {
  font-weight: 500;
  color: #333;
}

.remove-attachment-btn {
  background-color: #dc3545;
  color: white;
  border: none;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.875rem;
}

.remove-attachment-btn:hover {
  background-color: #c82333;
}
</style>