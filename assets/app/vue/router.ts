import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';

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

// Zendesk Contact Form (Support)
import ContactView from '@/views/ContactView/index.vue';
import SignUpView from '@/views/SignUpView/index.vue';

// Special Error Route
import ErrorView from '@/views/ErrorView/index.vue';

// If the page template is marked as error page, only show the error page.
const routes: RouteRecordRaw[] = window._page?.isErrorPage ? [
  {
    path: '/',
    name: 'error',
    component: ErrorView,
    meta: {
      isPublic: true,
      useAppTemplate: false,
    }
  }
] : [
  // Accounts Routes
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/sign-up',
    name: 'sign-up',
    component: SignUpView, // If we lazy-load this they'll see an ugly screen flash.
    meta: {
      isPublic: true,
      useAppTemplate: false,
    }
  },
  {
    path: '/sign-up/complete', // This is the "Check your email" page after sign-up.
    name: 'sign-up-complete',
    component: SignUpView, // If we lazy-load this they'll see an ugly screen flash.
    meta: {
      isPublic: true,
      useAppTemplate: false,
    }
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
  // Zendesk Contact Form (Support)
  {
    path: '/contact',
    name: 'contact',
    component: ContactView,
    meta: {
      isPublic: true,
    },
  },
];

const router = createRouter({
  history: createWebHistory('/'),
  routes: routes,
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
  const isErrorPage = window._page?.isErrorPage || false;
  // Annoying logic here, split up into nested if to be more readable.
  if (isErrorPage) {
    // Either go the error page, or short-circuit the function to avoid redirect loop
    if (to.name === 'error') {
      return true;
    }

    return { name: 'error' }
  }

  const isAuthenticated = window._page?.isAuthenticated;
  const hasActiveSubscription = window._page?.hasActiveSubscription;
  const isAwaitingPaymentVerification = window._page?.isAwaitingPaymentVerification;
  const sendToSubscribe = isAwaitingPaymentVerification || !hasActiveSubscription;

  // Don't let unauthenticated users anywhere except the home view
  if (!isAuthenticated && !to.meta?.isPublic) {
    // Login is done through Django routing and not Vue router
    window.location.href = '/login/';
    return false;
  }

  // Don't let unsubscribed users anywhere except the subscribe view
  if (isAuthenticated && sendToSubscribe && !['subscribe', 'contact'].includes(to.name.toString())) {
    return { name: 'subscribe' };
  } else if (isAuthenticated && !sendToSubscribe && to.name === 'subscribe') {
    return { name: 'dashboard' };
  }

  return true;
});

export default router;
