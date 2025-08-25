<script setup lang="ts">

import InlineInput from "@/views/DashboardView/components/InlineInput.vue";
import ContentSection from "@/views/DashboardView/components/ContentSection.vue";
import Divider from "@/views/DashboardView/components/Divider.vue";
import ServicesSection from "@/views/DashboardView/components/ServicesSection.vue";
</script>

<script lang="ts">
import {reactive} from "vue";

export default {
  name: 'DashboardView'
};

const formValues = reactive({
  email: window._page.userEmail,
  password: null,
  mfa: null,
  recoveryEmail: null,
  recoveryPhone: null,
});

</script>

<template>
  <div id="content">
    <section class="content-column">
      <content-section class="content-section">
        <h1>My Account</h1>
        <div class="fields">
        <inline-input v-model="formValues.email" :label="$t('dashboard.fields.email')"></inline-input>
        <divider/>
        <inline-input v-model="formValues.password" :label="$t('dashboard.fields.password')"></inline-input>
        <divider/>
        <inline-input v-model="formValues.mfa" :label="$t('dashboard.fields.mfa')"></inline-input>
        <divider/>
        <inline-input v-model="formValues.recoveryEmail" :label="$t('dashboard.fields.recovery-email')"></inline-input>
        <divider/>
        <inline-input v-model="formValues.recoveryPhone" :label="$t('dashboard.fields.recovery-phone')"></inline-input>
        </div>
      </content-section>
      <content-section class="content-section">
        <h1>Privacy & Data</h1>
        <inline-input v-model="formValues.email" label="Email"></inline-input>
      </content-section>
    </section>
    <divider type="vertical"/>
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

.fields {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
