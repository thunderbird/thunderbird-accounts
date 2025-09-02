import {createApp} from 'vue';
import router from '@/../router';
import MainApp from "@/App.vue";
import i18n from '@/../composables/i18n';

import '@thunderbirdops/services-ui/style.css';
import SelfServeForm from '@/components/SelfServeForm.vue';
import SignInToSignUpForm from '@/components/SignInToSignUpForm.vue';
import SignUpFlowForm from '@/components/SignUpFlowForm.vue';
import AccountInfoForm from '@/components/AccountInfoForm.vue';
import CheckoutFlow from '@/components/CheckoutFlow.vue';
import ContactSupportForm from '@/components/ContactSupportForm.vue';

const vueApps = [
  // Self Serve - App Password Page
  {
    id: 'selfServeForm',
    sfc: SelfServeForm,
  },
  // Self Serve - Account Info Page
  {
    id: 'accountInfoForm',
    sfc: AccountInfoForm,
  },
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

for (const app of vueApps) {
  if (window.document.getElementById(app.id)) {
    const form = createApp(app.sfc);
    form.mount(`#${app.id}`);
  }
}


// FIXME: Remove this hack when we fully implement the re-design
const app = createApp(MainApp);
app.use(router);
app.use(i18n)

// This isn't a module, so wait until the document is loaded before mounting
window.addEventListener('load', async () => {
  // Load our l10n messages once the template is fully rendered.
  //i18n.global.mergeLocaleMessage('en', {...window?._l10n ?? {}})
  app.mount('#app');
  await router.replace(window.location.pathname);
});

// Define our `_page` namespace as a generic so typescript stops complaining about it
declare global {
    interface Window { _page: any; }
}
