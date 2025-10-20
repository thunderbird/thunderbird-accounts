import { createMemoryHistory, createRouter, onBeforeRouteUpdate } from "vue-router";
import LoginView from "@/vue/views/LoginView/index.vue";
import RegisterView from "@/vue/views/RegisterView/index.vue";
import ForgotPasswordView from "@/vue/views/ForgotPasswordView/index.vue";
import PageExpiredView from "@/vue/views/PageExpiredView/index.vue";
import UpdatePasswordView from "@/vue/views/UpdatePasswordView/index.vue";
import RouteNotImplementedView from "./vue/views/RouteNotImplementedView/index.vue";
import LogoutView from "./vue/views/LogoutView/index.vue";
import ErrorView from "./vue/views/ErrorView/index.vue";
import InfoView from "./vue/views/InfoView/index.vue";
import VerifyEmailView from "./vue/views/VerifyEmailView/index.vue";
import ConfigToptView from "./vue/views/ConfigToptView/index.vue";
import LoginTotpView from "./vue/views/LoginTotpView/index.vue";
import DeleteCredentialView from "./vue/views/DeleteCredentialView/index.vue";

/**
 * Don't specify routes, as they're not absolute in keycloak.
 * Just make sure the pageId and route name match, and App.vue will
 * read/push the current route based on the template selected.
 */
const routes = [
  {
    name: 'login',
    component: LoginView,
  },
  {
    name: 'register',
    component: RegisterView,
  },
  {
    name: 'login-reset-password',
    component: ForgotPasswordView,
  },
  {
    name: 'login-update-password',
    component: UpdatePasswordView,
  },
  {
    name: 'login-verify-email',
    component: VerifyEmailView,
  },
  {
    name: 'login-page-expired',
    component: PageExpiredView,
  },
  {
    name: 'logout-confirm',
    component: LogoutView,
  },
  {
    name: 'login-config-totp',
    component: ConfigToptView,
  },
  {
    name: 'login-otp',
    component: LoginTotpView,
  },
  {
    name: 'login-username',
    component: LoginView,
    props: {
      hidePassword: true,
    }
  },
  {
    name: 'delete-credential',
    component: DeleteCredentialView,
  },
  {
    name: 'info',
    component: InfoView,
  },
  {
    name: 'error',
    component: ErrorView,
  },
  {
    name: 'route-not-implemented',
    component: RouteNotImplementedView,
  }
];

// create router object to export
const router = createRouter({
  history: createMemoryHistory(),
  routes,
});

export default router;
