import { ref, computed, watch, nextTick } from 'vue';

export const FTUE_STEPS = {
  INITIAL: 0,
  CONNECT_EMAIL: 1,
  APP_PASSWORDS: 2,
  EMAIL_ALIASES: 3,
  CUSTOM_DOMAINS: 4,
  FINAL: 5,
} as const;

type FtueStepId = typeof FTUE_STEPS[keyof typeof FTUE_STEPS];

interface StepConfig {
  targetId?: string;
  teleportTarget?: string;
  titleKey?: string;
  textKey?: string;
  subtitleNextStepKey?: string;
  showBack?: boolean;
  variant?: 'section' | 'header' | 'welcome';
  nextLabelKey?: string;
}

const FTUE_STORAGE_KEY = 'tb_accounts_ftue_completed';
const TOUR_CARD_SELECTOR = '[data-tour-card]';

// Get the initial state of the FTUE from localStorage or return true if not available
const getInitialState = () => {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem(FTUE_STORAGE_KEY) !== 'true';
  }

  return true;
};

const currentStep = ref<FtueStepId>(FTUE_STEPS.INITIAL);
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
  const steps: Record<FtueStepId, StepConfig> = {
    [FTUE_STEPS.INITIAL]: {
      teleportTarget: '#tour-target-header',
      titleKey: 'views.mail.ftue.initialWelcomeTitle',
      textKey: 'views.mail.ftue.initialWelcomeDescription',
      variant: 'welcome',
      nextLabelKey: 'views.mail.ftue.letsGo',
    },
    [FTUE_STEPS.CONNECT_EMAIL]: {
      targetId: 'connect-email',
      teleportTarget: '#tour-target-connect-email',
      textKey: 'views.mail.ftue.step1Text',
      subtitleNextStepKey: 'views.mail.ftue.appPassword',
      showBack: false,
    },
    [FTUE_STEPS.APP_PASSWORDS]: {
      targetId: 'email-settings',
      teleportTarget: '#tour-target-app-passwords',
      textKey: 'views.mail.ftue.step2Text',
      subtitleNextStepKey: 'views.mail.ftue.emailAliases',
      showBack: true,
    },
    [FTUE_STEPS.EMAIL_ALIASES]: {
      targetId: 'email-aliases',
      teleportTarget: '#tour-target-email-aliases',
      textKey: 'views.mail.ftue.step3Text',
      subtitleNextStepKey: 'views.mail.ftue.customDomains',
      showBack: true,
    },
    [FTUE_STEPS.CUSTOM_DOMAINS]: {
      targetId: 'custom-domains',
      teleportTarget: '#tour-target-custom-domains',
      textKey: 'views.mail.ftue.step4Text',
      subtitleNextStepKey: 'views.mail.ftue.yourAccount',
      showBack: true,
    },
    [FTUE_STEPS.FINAL]: {
      teleportTarget: '#tour-target-header',
      textKey: 'views.mail.ftue.step5Text',
      showBack: true,
      variant: 'header',
      nextLabelKey: 'views.mail.ftue.done',
    },
  };

  const currentStepConfig = computed(() => steps[currentStep.value]);

  const next = () => {
    if (currentStep.value < FTUE_STEPS.FINAL) {
      currentStep.value++;
    } else {
      showFTUE.value = false;
    }
  };

  const back = () => {
    if (currentStep.value > FTUE_STEPS.INITIAL) {
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

    const step = steps[newStep];

    if (step.targetId) {
      const element = document.getElementById(step.targetId);

      if (element) {
        element.scrollIntoView({ behavior, block: 'center' });
      }
    }

    focusTourCard();
  });

  return {
    currentStep,
    currentStepConfig,
    showFTUE,
    next,
    back,
    skip
  };
};

