<script setup lang="ts">
/**
 * Not actually an input anymore...
 */
import {LinkButton} from "@thunderbirdops/services-ui";

interface PropTypes {
  label: string,
  value: string,
  showChangeLink?: boolean
}

const props = withDefaults(defineProps<PropTypes>(), {showChangeLink: false});
const emit = defineEmits(['click']);
const onChange = (evt: PointerEvent) => {
  emit('click', { ...evt, value: props.label });
}
</script>


<template>
  <div class="field">
    <div class="wrapper">
      <span class="label">
        {{ label }}
      </span>
      <span class="value">{{ value }}</span>
    </div>
    <link-button @click="onChange" v-if="showChangeLink">{{ $t('dashboard.inline-input.change') }}</link-button>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  width: 100%;
  justify-content: space-between;
}

.wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  color: var(--colour-ti-base);
  line-height: var(--line-height-input);
  font-weight: 400;
  font-size: 16px;
}

.label {
  width: 100%;
  font-weight: 600;
}

.value {
  line-height: 1.32;
}

</style>
