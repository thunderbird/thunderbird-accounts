<script setup>
import { ref } from "vue";
import { NoticeBar, TextInput, TextArea, SelectInput, PrimaryButton } from "@thunderbirdops/services-ui";
import CsrfToken from "@/components/CsrfToken.vue";

const csrfToken = ref(window._page.csrfToken);
const errorText = ref(window._page.formError);
const successText = ref('');
const isSubmitting = ref(false);
const form = ref({
  email: window._page?.userEmail || '',
  subject: '',
  product: '',
  type: '',
  description: '',
  attachments: []
})
const formRef = ref(null)
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
  addFilesToForm(files)
  event.target.value = ''
}

const handleDrop = async (event) => {
  const files = event.dataTransfer.files
  addFilesToForm(files)
}

const addFilesToForm = (files) => {
  for (let file of files) {
    // Check if file already exists to avoid duplicates
    const existingFile = form.value.attachments.find(att => 
      att.file.name === file.name && att.file.size === file.size
    )
    
    if (!existingFile) {
      form.value.attachments.push({
        file: file,
        filename: file.name,
        size: file.size
      })
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

  formRef.value.reset()
}

const handleSubmit = async () => {
  if (isSubmitting.value) return;
  
  errorText.value = ''
  successText.value = ''
  isSubmitting.value = true

  try {
    const { email, subject, product, type, description, attachments } = form.value;

    // Create FormData instead of JSON
    const formData = new FormData()
    formData.append('email', email)
    formData.append('subject', subject)
    formData.append('product', product)
    formData.append('type', type)
    formData.append('description', description)

    attachments.forEach((attachment) => {
      formData.append('attachments', attachment.file)
    })

    const response = await fetch('/contact/submit', {
      mode: "same-origin",
      credentials: "include",
      method: 'POST',
      body: formData,
      headers: {
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
  } catch (error) {
    console.error('Submit error:', error)
    errorText.value = 'Failed to submit contact form. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}

</script>

<template>
  <notice-bar type="error" v-if="errorText" class="notice">{{ errorText }}</notice-bar>
  <notice-bar type="success" v-if="successText" class="notice">{{ successText }}</notice-bar>

  <form @submit.prevent="handleSubmit" method="post" action="/contact/submit" ref="formRef">
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
    <text-area
      name="description"
      v-model="form.description"
      required="required"
      data-testid="contact-description-input"
    >
      Description*
    </text-area>

    <div
      class="form-group file-dropzone"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileSelect"
      role="button"
      aria-label="Upload files"
    >
      <p v-if="form.attachments.length === 0">Drag & drop files here, or click to upload</p>
      <p v-else>{{ form.attachments.length }} file(s) selected. Drag & drop more files here, or click to upload</p>
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

    <div class="form-group">
      <primary-button 
        @click.capture="handleSubmit" 
        data-testid="contact-submit-btn"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? 'Submitting...' : 'Submit' }}
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
  margin-block: 1rem;
  max-width: 50%;
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