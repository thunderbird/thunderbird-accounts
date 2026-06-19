import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';

// Accounts Routes
import DashboardView from '@/views/DashboardView/index.vue';
import ManageMfaView from '@/views/ManageMfaView/index.vue';
import PrivacyAndDataView from '@/views/PrivacyAndDataView.vue';
import SubscribeView from '@/views/SubscribeView/index.vue';
import TosPrivacyView from '@/views/TosPrivacyView/index.vue';

// Thundermail Routes
import MailView from '@/views/MailView/index.vue';
import SecuritySettingsView from '@/views/MailView/views/SecuritySettingsView/index.vue';

// Zendesk Contact Form (Support)
import ContactView from '@/views/ContactView/index.vue';
import SignUpView from '@/views/SignUpView/index.vue';

// Special Error Route
import ErrorView from '@/views/ErrorView/index.vue';
import { TBPRO_WAIT_LIST } from './defines';
import { CAN_I_SIGN_UP_RESPONSES } from './types';

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
    },
    beforeEnter: (async (to, from) => {
      /* This is a bit too long but we cannot use beforeEnter in-component. :( */
      let failQueryParam = '';

      if (to.query?.email) {
        // Encode the email if it needs to be encoded
        const email = encodeURIComponent(to.query.email as string);

        try {
          const response = await fetch('/api/v1/auth/can-i-sign-up/', {
            method: 'POST',
            body: JSON.stringify({
              email,
            }),
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': window._page?.csrfToken,
            },
          });

          const data = await response.json();
          if (data?.go_to === CAN_I_SIGN_UP_RESPONSES.SIGN_UP) { // continue along with the request
            return true; 
          } else if (data?.go_to === CAN_I_SIGN_UP_RESPONSES.LOGIN) { // Ship to login, we don't use login hints here!
            window.location.href = '/';
            return false;
          } else if (data?.detail) { // rate limited

            // A small hack
            console.error("Sign-up rate limit reached:", data?.detail);
            window._page.errorTitle = data?.detail;
            window.history.pushState(to.fullPath, '', window.location.href);
            return { name: 'rate-limit', replace: false };
          }

          failQueryParam = `?email=${email}`;
        } catch (e) {
          console.error("Failed to fetch allowed status for the sign up page. Error: ", e);
        }
      }

      // Fail state, send them to the wait list.
      window.location.href = `${TBPRO_WAIT_LIST}${failQueryParam}`;
      return false;
    }),
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
  // Rate-limit page
  {
    path: '/chill', 
    name: 'rate-limit',
    component: ErrorView,
    props: {
      isRateLimit: true,
    },
    meta: {
      isPublic: true,
      useAppTemplate: false,
    }
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
