import { createMemoryHistory, createRouter, onBeforeRouteUpdate } from "vue-router";
import LoginView from "@/vue/views/LoginView/index.vue";
import RegisterView from "@/vue/views/RegisterView/index.vue";
import ForgotPasswordView from "@/vue/views/ForgotPasswordView/index.vue";
import PageExpiredView from "@/vue/views/PageExpiredView/index.vue";
import UpdatePasswordView from "@/vue/views/UpdatePasswordView/index.vue";
import RouteNotImplementedView from "./vue/views/RouteNotImplementedView/index.vue";
import LogoutView from "./vue/views/LogoutView/index.vue";

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
    name: 'login-page-expired',
    component: PageExpiredView,
  },
  {
    name: 'logout-confirm',
    component: LogoutView,
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
