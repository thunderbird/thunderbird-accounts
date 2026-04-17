import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';

// Accounts Routes
import DashboardView from '@/views/DashboardView/index.vue';
import ManageMfaView from '@/views/ManageMfaView/index.vue';
import PrivacyAndDataView from '@/views/PrivacyAndDataView.vue';
import PrivacyView from '@/views/PrivacyView.vue';
import SubscribeView from '@/views/SubscribeView/index.vue';
import TermsView from '@/views/TermsView.vue';
import TosPrivacyView from '@/views/TosPrivacyView/index.vue';

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
  // Root path
  {
    path: '/',
    redirect: '/mail'
  },
  // Accounts Routes
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
  {
    path: '/tos-privacy',
    name: 'tos-privacy',
    component: TosPrivacyView,
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
  // Fallback 404 page
  {
    path: '/:pathMatch(.*)*', 
    name: 'not-found',
    component: ErrorView,
    props: {
      is404: true,
    },
    meta: {
      isPublic: true,
      useAppTemplate: false,
    }
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
  const routeName = to.name?.toString();

  // Unauthenticated users can only visit public routes
  if (!isAuthenticated) {
    if (!to.meta?.isPublic) {
      window.location.href = '/login/';
      return false;
    }
    return true;
  }

  // --- Authenticated users below ---
  // Guards are ordered by priority: TOS > subscription > normal access.

  const allowedFor = {
    tos: ['tos-privacy', 'contact'],
    subscription: ['subscribe', 'contact', 'tos-privacy'],
  };

  if (window._page?.needsTosAcceptance && !allowedFor.tos.includes(routeName)) {
    return { name: 'tos-privacy' };
  }

  const needsSubscription = window._page?.isAwaitingPaymentVerification || !window._page?.hasActiveSubscription;

  if (needsSubscription && !allowedFor.subscription.includes(routeName)) {
    return { name: 'subscribe' };
  }

  if (!needsSubscription && routeName === 'subscribe') {
    return { name: 'mail' };
  }

  return true;
});

export default router;
