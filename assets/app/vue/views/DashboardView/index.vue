<script setup lang="ts">

import InlineInput from "@/views/DashboardView/components/InlineInput.vue";
import ContentSection from "@/views/DashboardView/components/ContentSection.vue";
import VerticalDivider from "@/views/DashboardView/components/VerticalDivider.vue";
import ServicesSection from "@/views/DashboardView/components/ServicesSection.vue";
</script>

<script lang="ts">
import {reactive} from "vue";

export default {
  name: 'DashboardView'
};

const formValues = reactive({
  email: window._page.userEmail
});

</script>

<template>
  <div id="content">
    <section class="content-column">
      <content-section class="content-section">
        <h1>My Account</h1>
        <inline-input v-model="formValues.email" label="Email"></inline-input>
      </content-section>
      <content-section class="content-section">
        <h1>Privacy & Data</h1>
        <inline-input v-model="formValues.email" label="Email"></inline-input>
      </content-section>
    </section>
    <vertical-divider/>
    <section class="content-column">
      <h1>My Services</h1>
      <services-section></services-section>
    </section>
  </div>
</template>

<style scoped>
#content {
  display: flex;
  height: 100%;
  justify-content: center;
  gap: 27px;
}

.content-column {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.content-section {
  width: 568px;
}
</style>
