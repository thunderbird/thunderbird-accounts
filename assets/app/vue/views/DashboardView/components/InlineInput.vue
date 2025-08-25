<script setup lang="ts">
import {LinkButton, TextInput} from "@thunderbirdops/services-ui";
import {ref} from "vue";


interface PropTypes {
  label: string,
}
defineProps<PropTypes>();
const model = defineModel<string>();
const readMode = ref<boolean>(true);
const onChange = () => {
  console.log('read me?', readMode.value);
  readMode.value = false;
}
</script>

<template>
  <div class="field">
  <text-input v-model="model" :disabled="readMode" :name="label">{{ label }}</text-input>
  <link-button @click="onChange">{{ $t('dashboard.inline-input.change') }}</link-button>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  width: 100%;
  justify-content: space-between;
}
</style>
