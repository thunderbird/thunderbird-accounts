<script setup lang="ts">

</script>

<template>
<section class="services">
  <ul class="services-list">
    <li>{{ $t('services.thundermail') }}</li>
    <li>{{ $t('services.appointment') }}</li>
    <li>{{ $t('services.send') }}</li>
  </ul>
</section>
</template>

<style scoped>
.services {
  width: 345px;
  flex-grow: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin: 15px 0 0;
  padding: 24px;
  border-radius: 24px;
  box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05), 1px 1px 0 0 rgba(255, 255, 255, 0.6);
  background-color: rgba(228, 228, 231, 0.5);
}

.services-list {
  list-style: none;
  padding: 0;
  display: flex;
  gap: 30px;
}
</style>
