import { createRouter, createWebHistory } from 'vue-router';

// Accounts Routes
import HomeView from '@/views/HomeView.vue';
import DashboardView from '@/views/DashboardView/index.vue';
import ManageMfaView from '@/views/ManageMfaView/index.vue';
import PrivacyAndDataView from '@/views/PrivacyAndDataView.vue';
import PrivacyView from '@/views/PrivacyView.vue';
import TermsView from '@/views/TermsView.vue';

// Thundermail Routes
import MailView from '@/views/MailView/index.vue';
import SecuritySettingsView from '@/views/MailView/views/SecuritySettingsView/index.vue';

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    // Accounts Routes
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
    // Thundermail Routes
    {
      path: '/mail',
      name: 'mail',
      component: MailView,
    },
    {
      path: '/mail/security-settings',
      name: 'mail-security-settings',
      component: SecuritySettingsView,
    },
    // Footer links (shared between Accounts and Thundermail)
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
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return {
        el: to.hash
      }
    }

    if (savedPosition) {
      return savedPosition;
    }

    return { top: 0, left: 0 }
  }
});

export default router;
