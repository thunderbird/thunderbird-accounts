import { createRouter, createWebHistory } from 'vue-router';

// Accounts Routes
import DashboardView from '@/views/DashboardView/index.vue';
import ManageMfaView from '@/views/ManageMfaView/index.vue';
import PrivacyAndDataView from '@/views/PrivacyAndDataView.vue';
import PrivacyView from '@/views/PrivacyView.vue';
import SubscribeView from '@/views/SubscribeView/index.vue';
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
      redirect: '/dashboard'
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
      meta: {
        isPublic: true,
      },
    },
    {
      path: '/terms',
      name: 'terms',
      component: TermsView,
      meta: {
        isPublic: true,
      },
    },
    // Sign Up / Subscribe
    {
      path: '/subscribe',
      name: 'subscribe',
      component: SubscribeView,
    },
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return {
        el: to.hash,
      };
    }

    if (savedPosition) {
      return savedPosition;
    }

    return { top: 0, left: 0 };
  },
});

router.beforeEach((to, _from) => {
  const isAuthenticated = window._page?.isAuthenticated;
  const hasActiveSubscription = window._page?.hasActiveSubscription;
  const isAwaitingPaymentVerification = window._page?.isAwaitingPaymentVerification;
  const sendToSubscribe = isAwaitingPaymentVerification || !hasActiveSubscription;

  // Don't let unauthenticated users anywhere except the home view
  if (!isAuthenticated && !to.meta?.isPublic) {
    // Login is done through Django routing and not Vue router
    window.location.href = '/login/';
    return;
  }

  // Don't let unsubscribed users anywhere except the subscribe view
  if (isAuthenticated && sendToSubscribe && to.name !== 'subscribe') {
    return { name: 'subscribe' };
  } else if (isAuthenticated && !sendToSubscribe && to.name === 'subscribe') {
    return { name: 'dashboard' };
  }

  return true;
});

export default router;
