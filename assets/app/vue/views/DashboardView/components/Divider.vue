<script setup lang="ts">
/**
 * This could be a <hr/> but there's no <vr/> :(
 */
interface PropTypes {
  type?: 'horizontal' | 'vertical'
};
withDefaults(defineProps<PropTypes>(), {
  type: 'horizontal'
});
</script>

<template>
  <div :class="type" class="divider"></div>
</template>

<style scoped>
.divider {
  box-shadow: 1px 0 0 0 #fff;
  background-color: #e4e4e7;
}

.horizontal {
  min-width: 100%;
  min-height: 1px;
}

.vertical {
  min-width: 1px;
  min-height: 100%;
}
</style>
