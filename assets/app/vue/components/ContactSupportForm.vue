<script setup>
import { ref } from "vue";
import { NoticeBar } from "@thunderbirdops/services-ui";
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
        <option value="accounts___login">Accounts & Login</option>
        <option value="technical">Technical</option>
        <option value="provide_feedback_or_request_features">Provide Feedback or Request Features</option>
        <option value="payments___billing">Payments & Billing</option>
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

.form-button {
  padding: 0.6rem 1.2rem;
  font-size: 1rem;
  cursor: pointer;
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