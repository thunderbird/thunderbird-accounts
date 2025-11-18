<script setup lang="ts">
import { TextInput } from '@thunderbirdops/services-ui';

/**
 * This component is a simple wrapper for native HTML input elements.
 * It is used alongside the <component :is="" /> Vue component
 * to handle dynamic components that we might not yet have a dedicated custom component for.
*/
const props = defineProps<{
  modelValue: string | number | null | undefined
  type?: string
  name?: string
  required?: boolean
}>();
const emit = defineEmits<{ (e: 'update:modelValue', v: any): void }>();

function onInput(e: Event) {
  const el = e.target as HTMLInputElement;
  const value =
    props.type === 'number'
      ? (el.value === '' ? '' : el.valueAsNumber)
      : el.value;
  emit('update:modelValue', value);
}
</script>

<template>
  <text-input
    v-bind="$attrs"
    :type="type"
    :name="name"
    :required="required"
    :value="modelValue as any"
    @input="onInput"
  />
</template>
