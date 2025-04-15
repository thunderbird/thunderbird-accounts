import { createApp } from 'vue';
import '@thunderbirdops/services-ui/style.css';
import SelfServeForm from '@/components/SelfServeForm.vue';
import SignInToSignUpForm from '@/components/SignInToSignUpForm.vue';
import SignUpFlowForm from '@/components/SignUpFlowForm.vue';
import AccountInfoForm from '@/components/AccountInfoForm.vue';
import CheckoutFlow from '@/components/CheckoutFlow.vue';

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
];

for (const app of vueApps) {
  if (document.getElementById(app.id)) {
    const form = createApp(app.sfc);
    form.mount(`#${app.id}`);
  }
}
