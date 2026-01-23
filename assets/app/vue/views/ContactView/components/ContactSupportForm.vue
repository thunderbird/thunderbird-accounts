<script setup lang="ts">
import { ref, onMounted, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { NoticeBar, TextInput, TextArea, SelectInput, PrimaryButton, NoticeBarTypes, CheckboxInput, LoadingSkeleton } from '@thunderbirdops/services-ui';
import CsrfToken from '@/components/forms/CsrfToken.vue';
import NativeInputWrapper from './NativeInputWrapper.vue';

// Types
import { ContactFieldsAPIResponse, TicketField } from '../types';

// Zendesk Ticket Field <-> Vue Component mapping
// https://developer.zendesk.com/api-reference/ticketing/tickets/ticket_fields/#create-ticket-field
const TICKET_FIELD_TYPE_TO_COMPONENT = {
  'text': TextInput,
  'textarea': TextArea,
  'checkbox': CheckboxInput,
  'date': NativeInputWrapper,
  'integer': NativeInputWrapper,
  'decimal': NativeInputWrapper,
  'regexp': TextInput,
  'partialcreditcard': '', // TODO: Define a partial credit card input component, if needed
  'multiselect': '', // TODO: Define a multi-select input component, if needed
  'tagger': SelectInput,
  'lookup': '', // TODO: Define a lookup input component, if needed
  'subject': TextInput,
  'description': TextArea,
};

const { t } = useI18n();

const csrfTokenVal = ref(window._page.csrfToken);
const errorText = ref(window._page.formError);
const successText = ref('');
const isSubmitting = ref(false);
const form = ref({
  email: window._page?.userEmail || '',
  name: window._page?.userFullName || '',
  attachments: [],
});
const formRef = ref(null);
const fileInput = ref(null);
const isLoadingFormFields = ref(true);

// services-ui's TextInput and TextArea field references for resetting form state
const emailInput = useTemplateRef('emailInput');
const dynamicFields = ref<TicketField[]>([]);

const nativeAttrsForField = (field: TicketField) => {
  switch (field.type) {
    case 'date':
      return { type: 'date' };
    case 'integer':
      return { type: 'number' };
    case 'decimal':
      return { type: 'number' };
    default:
      return {};
  }
};

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

    const data: ContactFieldsAPIResponse = await response.json();

    if (data.success && data.ticket_fields) {
      dynamicFields.value = data.ticket_fields;

      // Initialize dynamic field values in the form object
      data.ticket_fields.forEach((field) => {
        if (!(field.title in form.value)) {
          form.value[field.title] = '';
        }
      });
    } else {
      errorText.value = t('views.contact.errorFetchingFields');
    }
  } catch (error) {
    errorText.value = error;
  } finally {
    isLoadingFormFields.value = false;
  }
};

const resetForm = () => {
  // Reset fixed form fields (not dynamic fields)
  form.value = {
    email: '',
    name: '',
    attachments: [],
  };

  // Reset dynamic fields
  dynamicFields.value.forEach((field) => {
    form.value[field.title] = '';
  });

  errorText.value = '';
  successText.value = '';

  // services-ui's TextInput and TextArea components don't reset their internal state
  // when the form is reset, so we need to reset them manually
  emailInput.value.reset();
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
    const jsonData = {
      // Email is a fixed field
      email: form.value.email,
      name: form.value.name,
      fields: []
    };

    // Add all dynamic field values with structured data
    dynamicFields.value.forEach((field) => {
      const fieldValue = form.value[field.title];
      if (fieldValue !== undefined && fieldValue !== '') {
        jsonData.fields.push({
          id: field.id,
          title: field.title,
          value: fieldValue,
          type: field.type,
          required: field.required,
        });
      }
    });

    // Create FormData for multipart/form-data request
    const formData = new FormData();

    // Add JSON data as a string field
    formData.append('data', JSON.stringify(jsonData));

    // Add each file attachment
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
      errorText.value = data.error || t('views.contact.errorSubmittingForm');
      return;
    }

    resetForm();
    successText.value = t('views.contact.success');
  } catch (error) {
    errorText.value = error;
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(() => {
  fetchTicketFields();
});
</script>

<template>
  <notice-bar :type="NoticeBarTypes.Critical" v-if="errorText" class="notice">{{ errorText }}</notice-bar>
  <notice-bar :type="NoticeBarTypes.Success" v-if="successText" class="notice">{{ successText }}</notice-bar>

  <form @submit.prevent="handleSubmit" method="post" action="/contact/submit" ref="formRef">
    <!-- Email (always present) -->
    <text-input ref="emailInput" name="email" type="email" v-model="form.email" :required="true"
      data-testid="contact-email-input">
      {{ t('views.contact.emailAddressLabel') }}
    </text-input>

    <text-input ref="nameInput" name="name" type="text" v-model="form.name" :required="false"
      data-testid="contact-name-input">
      {{ t('views.contact.nameLabel') }}
    </text-input>

    <template v-if="isLoadingFormFields">
      <template v-for="i in 5" :key="i">
        <loading-skeleton :is-loading="true" class="loading-skeleton-field">
          <div />
        </loading-skeleton>
      </template>
    </template>

    <template v-else>
      <template v-for="field in dynamicFields" :key="field.id">
        <component
          :is="TICKET_FIELD_TYPE_TO_COMPONENT[field.type]"
          :ref="field.id"
          :name="field.title"
          v-model="form[field.title]"
          v-bind="nativeAttrsForField(field)"
          :required="field.required"
          :options="field.custom_field_options?.map((option) => ({ label: option.name, value: option.value }))"
          :data-testid="`contact-${field.title}-input`"
          :help="field.description"
        >
          {{ field.title }}
        </component>
      </template>
    </template>

    <div class="file-upload-container">
      <p>{{ t('views.contact.fileUploadLabel') }}</p>
      <div class="form-group file-dropzone" @dragover.prevent @drop.prevent="handleDrop" @click="triggerFileSelect"
        role="button" aria-label="Upload files">
        <p v-if="form.attachments.length === 0" class="file-dropzone-initial-text">
          {{ t('views.contact.dragAndDropFilesText') }}
        </p>
        <p v-else>
          {{ t('views.contact.filesSelectedText', { count: form.attachments.length }) }}
        </p>
        <input type="file" ref="fileInput" class="hidden file-input-button" multiple @change="handleFileSelect" />
      </div>
    </div>

    <ul v-if="form.attachments.length" class="attachment-list">
      <li v-for="(attachment, index) in form.attachments" :key="index">
        <span class="attachment-filename">{{ attachment.filename }}</span>
        <button @click="removeAttachment(index)" class="remove-attachment-btn">
          {{ t('views.contact.remove') }}
        </button>
      </li>
    </ul>

    <div class="form-group">
      <primary-button @click.capture="handleSubmit" data-testid="contact-submit-btn" :disabled="isSubmitting">
        {{ isSubmitting ? t('views.contact.submitting') : t('views.contact.submit') }}
      </primary-button>
    </div>

    <csrf-token></csrf-token>
  </form>
</template>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-block-start: 1rem;

  .loading-skeleton-field {
    height: 4.5rem !important; /* height is defined inline in services-ui */
    width: 100% !important; /* width is defined inline in services-ui */
  }

  .file-upload-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    color: var(--colour-ti-secondary);
    font-weight: 500;
  }
}

.form-group {
  margin-block-end: 1rem;

  &.file-dropzone {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    cursor: pointer;
    outline: none;
    min-height: 137px;
    box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05);
    /* Dashed border effect as we can't easily set the distance between the dashes */
    background-image:
      linear-gradient(to right, var(--colour-neutral-border) 0 12px, transparent 12px 100%),
      linear-gradient(to right, var(--colour-neutral-border) 0 12px, transparent 12px 100%),
      linear-gradient(to bottom, var(--colour-neutral-border) 0 12px, transparent 12px 100%),
      linear-gradient(to bottom, var(--colour-neutral-border) 0 12px, transparent 12px 100%);
    background-position: top left, bottom left, top left, top right;
    background-size: 16px 1px, 16px 1px, 1px 16px, 1px 16px;
    background-repeat: repeat-x, repeat-x, repeat-y, repeat-y;

    p {
      margin-block-end: 1rem;

      &.file-dropzone-initial-text {
        color: var(--colour-ti-muted);
        line-height: 1.32;
        font-weight: normal;
      }
    }

    .file-input-button {
      color: var(--colour-ti-muted);
      line-height: 1.23;
      font-size: 0.875rem;
      cursor: pointer;

      &::file-selector-button {
        background-color: var(--colour-neutral-base);
        color: var(--colour-primary-hover);
        border-radius: 8px;
        border: 1px solid var(--colour-ti-highlight);
        padding: 0.375rem 0.75rem;
        margin-inline-end: 0.75rem;
      }
    }

    &:hover {
      border-color: #888;
    }

    &:focus {
      border-color: #333;
    }
  }
}

/* Bug fix: select-input's labels have a .wrapper class with a max-width of 320px */
.wrapper {
  max-width: 100%;
}

.notice {
  margin-block: 1rem;
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
