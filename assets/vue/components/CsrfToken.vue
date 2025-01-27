<script setup>
import {ref} from "vue";

const csrfToken = ref(window._page.csrfToken);
</script>
<template>
  <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken"/>
</template>