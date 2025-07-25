import { createMemoryHistory, createRouter } from "vue-router";
import LoginView from "@/vue/views/LoginView/index.vue";
import RegisterView from "@/vue/views/RegisterView/index.vue";
import ForgotPassword from "@/vue/views/ForgotPassword/index.vue";


const routes = [
  {
    path: '/login-actions/authenticate',
    name: 'login',
    component: LoginView,
    alias: [
      // The main url when someone clicks login
      '/protocol/openid-connect/auth'
    ]
  },
  {
    path: '/login-actions/registration',
    name: 'register',
    component: RegisterView
  },
  {
    path: '/login-actions/reset-credentials',
    name: 'forgot-password',
    component: ForgotPassword,
  }
];

// create router object to export
const router = createRouter({
  history: createMemoryHistory(),
  routes,
});

export default router;
