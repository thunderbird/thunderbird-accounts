<script setup lang="ts">
import ContactSupportForm from './components/ContactSupportForm.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
</script>

<script lang="ts">
export default {
  name: 'ContactView',
};
</script>

<template>
  <h2>{{ t('views.contact.title') }}</h2>
  <span>{{ t('views.contact.requiredFieldsText') }}</span>

  <contact-support-form />
</template>