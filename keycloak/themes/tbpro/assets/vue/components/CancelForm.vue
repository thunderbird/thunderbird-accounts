<script setup>
import {ref, useTemplateRef, watch} from "vue";

defineProps({
  action: 'string',
  cancelId: 'string',
  cancelValue: 'string',
  cancelName: 'string',
});

const cancelForm = useTemplateRef('cancel-form');
const showForm = ref(false);

/**
 * Keycloak cancels / sends a user back by submitting the form with a specific name/value in the form data.
 * We emulate this with a hidden input that is rendered if they hit cancel.
 */
const cancel = () => {
  // Setup a one-time watch for the cancelForm to not be null
  watch(
    cancelForm,
    () => {
      cancelForm?.value?.submit();
    }, {once: true});

  // This will cause the cancelForm not be null
  showForm.value = true;
};

// Allow the submit action to be called
defineExpose({cancel});
</script>

<template>
  <form ref="cancel-form" method="POST" :action="action" v-if="showForm">
    <input type="hidden" :name="cancelName" :value="cancelValue" :id="cancelId"/>
  </form>
</template>
