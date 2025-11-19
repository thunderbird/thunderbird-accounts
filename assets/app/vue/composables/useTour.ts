import { ref, watch } from 'vue';

export const FTUE_STEPS = {
  INITIAL: 0,
  DASHBOARD: 1,
  CUSTOM_DOMAINS: 2,
  FINAL: 3,
}

const currentStep = ref(FTUE_STEPS.INITIAL);

// TODO: Change this to localStorage or something
const showFTUE = ref(true);

export const useTour = () => {
  const steps = [
    {
      id: FTUE_STEPS.INITIAL,
    },
    {
      id: FTUE_STEPS.DASHBOARD,
      targetId: 'dashboard',
    },
    {
      id: FTUE_STEPS.CUSTOM_DOMAINS,
      targetId: 'custom-domains',
    },
    {
      id: FTUE_STEPS.FINAL,
      targetId: 'email-settings',
    }
  ];

  const start = () => {
    currentStep.value = 1;
  };

  const next = () => {
    if (currentStep.value < steps.length - 1) {
      currentStep.value++;
    } else {
      showFTUE.value = false;
    }
  };

  const back = () => {
    if (currentStep.value > 0) {
      currentStep.value--;
    }
  };

  const skip = () => {
    showFTUE.value = false;
  };

  // Auto-scroll to target when step changes
  watch(currentStep, (newStep) => {
    if (!showFTUE.value) return;

    const noPrefersReducedMotion = window.matchMedia('(prefers-reduced-motion: no-preference)').matches;
    const behavior = noPrefersReducedMotion ? 'smooth' : 'auto';

    if (newStep === FTUE_STEPS.INITIAL) {
      window.scrollTo({ top: 0, behavior });
      return;
    }

    const step = steps.find(s => s.id === newStep);

    if (step && step.targetId) {
      const element = document.getElementById(step.targetId);

      if (element) {
        element.scrollIntoView({ behavior, block: 'center' });
      }
    }
  });

  return {
    currentStep,
    showFTUE,
    start,
    next,
    back,
    skip
  };
};

