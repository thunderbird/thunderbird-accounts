import { createRouter, createWebHistory } from 'vue-router';

import HomeView from '@/views/HomeView.vue';
import DashboardView from '@/views/DashboardView/index.vue';
import ManageMfaView from '@/views/ManageMfaView.vue';
import PrivacyAndDataView from '@/views/PrivacyAndDataView.vue';
import PrivacyView from '@/views/PrivacyView.vue';
import TermsView from '@/views/TermsView.vue';

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
    },
    {
      path: '/manage-mfa',
      name: 'manage-mfa',
      component: ManageMfaView,
    },
    {
      path: '/privacy-and-data',
      name: 'privacy-and-data',
      component: PrivacyAndDataView,
    },
    // Footer links
    {
      path: '/privacy',
      name: 'privacy',
      component: PrivacyView,
    },
    {
      path: '/terms',
      name: 'terms',
      component: TermsView,
    },
  ],
});

export default router;
