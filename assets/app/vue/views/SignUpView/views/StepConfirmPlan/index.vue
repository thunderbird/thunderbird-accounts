<script setup lang="ts">
import { NOT_INTERESTED_SURVEY_LINK } from '@/defines';
import PlanCard from '@/components/PlanCard.vue';
import SignUpLayout from '../../components/SignUpLayout.vue';
import { useSignUpFlowStore } from '../../stores/signUpFlowStore';

const signUpFlowStore = useSignUpFlowStore();
const { nextStep } = signUpFlowStore;

const onNotInterested = () => {
  window.location.href = NOT_INTERESTED_SURVEY_LINK;
};

const onSubmit = () => {
  nextStep();
}
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
    @submit="onSubmit"
  >
    <template v-slot:notice-bars>
      <slot name="notice-bars" />
    </template>
    <template v-slot:form-elements>
      <div class="plan-card-container">
        <plan-card />
      </div>
    </template>
  </sign-up-layout>
</template>

<style scoped>
.plan-card-container {
  margin-block-end: 1rem;
}
</style>
