import { ref, watch, nextTick } from 'vue';

export const FTUE_STEPS = {
  INITIAL: 0,
  CONNECT_EMAIL: 1,
  APP_PASSWORDS: 2,
  EMAIL_ALIASES: 3,
  CUSTOM_DOMAINS: 4,
  FINAL: 5,
} as const;

const FTUE_STORAGE_KEY = 'tb_accounts_ftue_completed';
const TOUR_CARD_SELECTOR = '[role="dialog"][tabindex="-1"]';

// Get the initial state of the FTUE from localStorage or return true if not available
const getInitialState = () => {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem(FTUE_STORAGE_KEY) !== 'true';
  }

  return true;
};

const currentStep = ref<typeof FTUE_STEPS[keyof typeof FTUE_STEPS]>(FTUE_STEPS.INITIAL);
const showFTUE = ref(getInitialState());

const onEscapeKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    showFTUE.value = false;
  }
};

const focusTourCard = () => {
  nextTick(() => {
    const card = document.querySelector<HTMLElement>(TOUR_CARD_SELECTOR);
    card?.focus();
  });
};

watch(showFTUE, (value) => {
  if (value) {
    document.addEventListener('keydown', onEscapeKey);
    return;
  }

  document.removeEventListener('keydown', onEscapeKey);

  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(FTUE_STORAGE_KEY, 'true');
  }
}, { immediate: true });

export const useTour = () => {
  const steps = [
    {
      id: FTUE_STEPS.INITIAL,
    },
    {
      id: FTUE_STEPS.CONNECT_EMAIL,
      targetId: 'connect-email',
    },
    {
      id: FTUE_STEPS.APP_PASSWORDS,
      targetId: 'email-settings',
    },
    {
      id: FTUE_STEPS.EMAIL_ALIASES,
      targetId: 'email-aliases',
    },
    {
      id: FTUE_STEPS.CUSTOM_DOMAINS,
      targetId: 'custom-domains',
    },
    {
      id: FTUE_STEPS.FINAL,
    }
  ];

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

  // Auto-scroll to target and move focus when step changes
  watch(currentStep, (newStep) => {
    if (!showFTUE.value) return;

    const noPrefersReducedMotion = window.matchMedia('(prefers-reduced-motion: no-preference)').matches;
    const behavior = noPrefersReducedMotion ? 'smooth' : 'auto';

    if (newStep === FTUE_STEPS.INITIAL || newStep === FTUE_STEPS.FINAL) {
      window.scrollTo({ top: 0, behavior });
      focusTourCard();
      return;
    }

    const step = steps.find(s => s.id === newStep);

    if (step && step.targetId) {
      const element = document.getElementById(step.targetId);

      if (element) {
        element.scrollIntoView({ behavior, block: 'center' });
      }
    }

    focusTourCard();
  });

  return {
    currentStep,
    showFTUE,
    next,
    back,
    skip
  };
};

