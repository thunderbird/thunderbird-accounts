// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createMemoryHistory, createRouter } from 'vue-router';
import i18n from '@/composables/i18n';
import HeaderBar from './HeaderBar.vue';

const mountHeaderBar = (pageData: Record<string, unknown>) => {
  (window as any)._page = { isAuthenticated: true, ...pageData };

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  });

  return mount(HeaderBar, {
    global: {
      plugins: [i18n, router],
      stubs: {
        // Render the default slot so we can see what's inside the router-link.
        RouterLink: { template: '<a><slot :href="\'/\'" :navigate="() => {}" /></a>' },
        AppDrawer: { template: '<div data-testid="app-drawer" />' },
        UserMenu: { template: '<div data-testid="user-menu" />' },
        IconButton: { template: '<button data-testid="settings-button"><slot /></button>' },
      },
    },
  });
};

afterEach(() => {
  delete (window as any)._page;
});

describe('HeaderBar', () => {
  it('shows the settings icon and app drawer for a paid user', () => {
    const wrapper = mountHeaderBar({ hasActiveSubscription: true, isAwaitingPaymentVerification: false });

    expect(wrapper.find('[data-testid="settings-button"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="app-drawer"]').exists()).toBe(true);
  });

  it('still shows them for a paid user who has not accepted the ToS yet', () => {
    const wrapper = mountHeaderBar({
      hasActiveSubscription: true,
      isAwaitingPaymentVerification: false,
      needsTosAcceptance: true,
    });

    expect(wrapper.find('[data-testid="settings-button"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="app-drawer"]').exists()).toBe(true);
  });

  it('hides them for a user without a subscription', () => {
    const wrapper = mountHeaderBar({ hasActiveSubscription: false });

    expect(wrapper.find('[data-testid="settings-button"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="app-drawer"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="user-menu"]').exists()).toBe(true);
  });

  it('hides them while payment verification is pending', () => {
    const wrapper = mountHeaderBar({ hasActiveSubscription: true, isAwaitingPaymentVerification: true });

    expect(wrapper.find('[data-testid="settings-button"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="app-drawer"]').exists()).toBe(false);
  });
});
