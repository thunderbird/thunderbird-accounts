<script lang="ts">
export default {
  name: 'MailView',
};
</script>

<template>
  <div class="mail-view" />
</template>

<style scoped>
.mail-view {
  display: flex;
  flex-direction: column;
}

.mail-view :deep(:not(:first-child) section) {
  margin-block-end: 2rem;
}
</style>
