import { createApp } from 'vue';
import '@thunderbirdops/services-ui/style.css';

// Forms (Kept as is for now)
import SignInToSignUpForm from '@/components/forms/SignInToSignUpForm.vue';
import SignUpFlowForm from '@/components/forms/SignUpFlowForm.vue';
import CheckoutFlow from '@/components/forms/CheckoutFlow.vue';
import ContactSupportForm from '@/components/forms/ContactSupportForm.vue';

// Vue App (Everything else)
import App from '@/App.vue';

const vueForms = [
  // Sign Up Page
  {
    id: 'signInToSignUpForm',
    sfc: SignInToSignUpForm,
  },
  {
    id: 'signUpFlowForm',
    sfc: SignUpFlowForm,
  },
  {
    id: 'checkoutFlow',
    sfc: CheckoutFlow,
  },
  {
    id: 'contactSupportForm',
    sfc: ContactSupportForm,
  },
];

if (window.document.getElementById('app')) {
  (async () => {

    // Only import router when we're actually on a Vue app route
    const { default: router } = await import('@/router');
    const { default: i18n } = await import('@/composables/i18n');

    const app = createApp(App);

    app.use(i18n);
    app.use(router);
    app.mount('#app');
  })();
} else {
  for (const vueForm of vueForms) {
    if (window.document.getElementById(vueForm.id)) {
      const form = createApp(vueForm.sfc);
      form.mount(`#${vueForm.id}`);
    }
  }
}
