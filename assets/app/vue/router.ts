import {createRouter, createWebHistory} from 'vue-router';

// Accounts Routes
import HomeView from '@/views/HomeView.vue';
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
      name: 'home',
      component: HomeView,
      meta: {
        isPublic: true,
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
      }
    },
    {
      path: '/terms',
      name: 'terms',
      component: TermsView,
      meta: {
        isPublic: true,
      }
    },
    // Sign Up / Subscribe
    {
      path: '/subscribe',
      name: 'subscribe',
      component: SubscribeView
    }
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

    return {top: 0, left: 0}
  }
});

router.beforeEach((to, from) => {
  const isAuthenticated = window._page?.isAuthenticated;
  const hasActiveSubscription = window._page?.hasActiveSubscription;

  // Don't let unauthenticated users anywhere except the home view
  if (!isAuthenticated && !to.meta?.isPublic) {
    return {name: 'home'};
  }

  // Don't let unsubscribed users anywhere except the subscribe view
  if (isAuthenticated && !hasActiveSubscription && to.name != 'subscribe') {
    return {name: 'subscribe'};
  }

  return true
})

export default router;
