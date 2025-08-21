<script setup lang="ts">
import { ref, onMounted, useTemplateRef } from 'vue';
import { NoticeBar, TextInput, TextArea, SelectInput, PrimaryButton, NoticeBarTypes } from '@thunderbirdops/services-ui';
import CsrfToken from '@/components/CsrfToken.vue';

const TICKET_CUSTOM_FIELD_NAMES = {
  PRODUCT: 'Product',
  TYPE_OF_REQUEST: 'Type of request',
};

const csrfTokenVal = ref(window._page.csrfToken);
const errorText = ref(window._page.formError);
const successText = ref('');
const isSubmitting = ref(false);
const form = ref({
  email: window._page?.userEmail || '',
  subject: '',
  product: '',
  type: '',
  description: '',
  attachments: [],
});
const formRef = ref(null);
const fileInput = ref(null);

// services-ui's TextInput and TextArea field references for resetting form state
const emailInput = useTemplateRef('emailInput');
const subjectInput = useTemplateRef('subjectInput');
const descriptionInput = useTemplateRef('descriptionInput');

// Dynamic options from API
const productOptions = ref([]);
const typeOptions = ref([]);

// Store field IDs for submission
const productFieldId = ref(null);
const typeFieldId = ref(null);

const triggerFileSelect = () => {
  fileInput.value?.click();
};

const handleFileSelect = async (event) => {
  const files = event.target.files;
  addFilesToForm(files);
  event.target.value = '';
};

const handleDrop = async (event) => {
  const files = event.dataTransfer.files;
  addFilesToForm(files);
};

const addFilesToForm = (files) => {
  for (const file of files) {
    // Check if file already exists to avoid duplicates
    const existingFile = form.value.attachments.find(
      (att) => att.file.name === file.name && att.file.size === file.size
    );

    if (!existingFile) {
      form.value.attachments.push({
        file: file,
        filename: file.name,
        size: file.size,
      });
    }
  }
};

const removeAttachment = (index) => {
  form.value.attachments.splice(index, 1);
};

const fetchTicketFields = async () => {
  try {
    const response = await fetch('/contact/fields', {
      method: 'GET',
      credentials: 'include',
    });

    const data = await response.json();

    if (data.success && data.ticket_fields) {
      // Process the ticket fields to populate the dropdowns
      const fields = data.ticket_fields;

      // Set Product field options and ID
      if (fields[TICKET_CUSTOM_FIELD_NAMES.PRODUCT]) {
        const productField = fields[TICKET_CUSTOM_FIELD_NAMES.PRODUCT];
        productOptions.value = productField.custom_field_options.map((option) => ({
          label: option.name,
          value: option.value,
        }));
        productFieldId.value = productField.id;
      }

      // Set Type of request field options and ID
      if (fields[TICKET_CUSTOM_FIELD_NAMES.TYPE_OF_REQUEST]) {
        const typeField = fields[TICKET_CUSTOM_FIELD_NAMES.TYPE_OF_REQUEST];
        typeOptions.value = typeField.custom_field_options.map((option) => ({
          label: option.name,
          value: option.value,
        }));
        typeFieldId.value = typeField.id;
      }
    }
  } catch (error) {
    console.error('Error fetching ticket fields:', error);
    errorText.value = 'Failed to fetch ticket fields. Please try again.';
  }
};

const resetForm = () => {
  form.value = {
    email: '',
    subject: '',
    product: '',
    type: '',
    description: '',
    attachments: [],
  };
  errorText.value = '';
  successText.value = '';

  // services-ui's TextInput and TextArea components don't reset their internal state
  // when the form is reset, so we need to reset them manually
  emailInput.value.reset();
  subjectInput.value.reset();
  descriptionInput.value.reset();

  formRef.value.reset();
};

const handleSubmit = async () => {
  if (isSubmitting.value) return;

  errorText.value = '';
  successText.value = '';

  if (!formRef.value.checkValidity()) {
    formRef.value.reportValidity();
    return;
  }

  isSubmitting.value = true;

  try {
    // Create FormData instead of JSON
    const formData = new FormData();
    formData.append('email', form.value.email);
    formData.append('subject', form.value.subject);
    formData.append('product', form.value.product);
    formData.append('product_field_id', productFieldId.value);
    formData.append('type', form.value.type);
    formData.append('type_field_id', typeFieldId.value);
    formData.append('description', form.value.description);

    form.value.attachments.forEach((attachment) => {
      formData.append('attachments', attachment.file);
    });

    const response = await fetch('/contact/submit', {
      mode: 'same-origin',
      credentials: 'include',
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': csrfTokenVal.value,
      },
    });

    const data = await response.json();

    if (!data.success) {
      errorText.value = data.error;
      return;
    }

    resetForm();
    successText.value = 'Your support request has been submitted successfully';
  } catch (error) {
    console.error('Submit error:', error);
    errorText.value = 'Failed to submit contact form. Please try again.';
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(() => {
  fetchTicketFields();
});
</script>

<template>
  <notice-bar :type="NoticeBarTypes.Error" v-if="errorText" class="notice">{{ errorText }}</notice-bar>
  <notice-bar :type="NoticeBarTypes.Success" v-if="successText" class="notice">{{ successText }}</notice-bar>

  <form @submit.prevent="handleSubmit" method="post" action="/contact/submit" ref="formRef">
    <!-- Email -->
    <text-input
      ref="emailInput"
      name="email"
      type="email"
      v-model="form.email"
      :required="true"
      data-testid="contact-email-input"
    >
      Your email address
    </text-input>

    <!-- Subject -->
    <text-input
      ref="subjectInput"
      name="subject"
      type="text"
      v-model="form.subject"
      :required="true"
      data-testid="contact-subject-input"
    >
      Subject
    </text-input>

    <!-- Product -->
    <select-input
      name="product"
      :options="productOptions"
      v-model="form.product"
      :required="true"
      data-testid="contact-product-input"
    >
      Product
    </select-input>

    <!-- Type of Request -->
    <select-input
      name="type"
      :options="typeOptions"
      v-model="form.type"
      :required="true"
      data-testid="contact-type-input"
    >
      Type of Request
    </select-input>

    <!-- Description -->
    <text-area
      ref="descriptionInput"
      name="description"
      v-model="form.description"
      :required="true"
      data-testid="contact-description-input"
    >
      Description
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
      <input type="file" ref="fileInput" class="hidden" multiple @change="handleFileSelect" />
    </div>

    <ul v-if="form.attachments.length" class="attachment-list">
      <li v-for="(attachment, index) in form.attachments" :key="index">
        <span class="attachment-filename">{{ attachment.filename }}</span>
        <button @click="removeAttachment(index)" class="remove-attachment-btn">Remove</button>
      </li>
    </ul>

    <div class="form-group">
      <primary-button @click.capture="handleSubmit" data-testid="contact-submit-btn" :disabled="isSubmitting">
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
