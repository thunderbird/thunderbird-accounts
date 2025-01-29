import {createApp} from "vue";
import '@thunderbirdops/services-ui/style.css';
import SelfServeForm from "@/components/SelfServeForm.vue";
import SignInToSignUpForm from "@/components/SignInToSignUpForm.vue";
import SignUpFlowForm from "@/components/SignUpFlowForm.vue";

/*
 * Self Serve - App Password Page
 */

if (document.getElementById('selfServeForm')) {
  const selfServeForm = createApp(SelfServeForm);
  selfServeForm.mount('#selfServeForm');
}

/*
 * Sign Up Page
 */

if (document.getElementById('signInToSignUpForm')) {
  const signInToSignUpForm = createApp(SignInToSignUpForm);
  signInToSignUpForm.mount('#signInToSignUpForm');
}

if (document.getElementById('signUpFlowForm')) {
  const signUpForm = createApp(SignUpFlowForm);
  signUpForm.mount('#signUpFlowForm');
}