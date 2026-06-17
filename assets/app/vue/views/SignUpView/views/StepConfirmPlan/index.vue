<script setup lang="ts">
import { NOT_INTERESTED_SURVEY_LINK } from '@/defines';
import PlanCard from '@/components/PlanCard.vue';
import SignUpLayout from '../../components/SignUpLayout.vue';

const onNotInterested = () => {
  window.location.href = NOT_INTERESTED_SURVEY_LINK;
};
</script>

<script lang="ts">
export default {
  name: 'StepConfirmPlan',
};
</script>

<template>
  <sign-up-layout
    step-id="step-confirm-plan"
    :title="$t('views.mail.views.signUp.stepConfirmPlan.title')"
    :subtitle="$t('views.mail.views.signUp.stepConfirmPlan.subtitle')"
    :submit-disabled="false"
    :submit-title="$t('views.mail.views.signUp.stepConfirmPlan.action')"
    :show-alternative-action="true"
    :alternative-action-title="$t('views.mail.views.signUp.stepConfirmPlan.notInterested')"
    @alternative-action="onNotInterested"
  >
    <template v-slot:notice-bars>
      <slot name="notice-bars" />
    </template>
    <template v-slot:form-elements>
      <plan-card />
    </template>
  </sign-up-layout>
</template>
