// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createMemoryHistory, createRouter } from 'vue-router';
import i18n from '@/composables/i18n';
import { WAFFLE_FLAG } from '@/types';
import HeaderBar from './HeaderBar.vue';

type PageOverrides = Partial<Window['_page']>;

const mountHeaderBar = async (pageOverrides: PageOverrides = {}, activeFlags: WAFFLE_FLAG[] = []) => {
  window._page = {
    isAuthenticated: true,
    userDisplayName: 'Test User',
    needsTosAcceptance: false,
    isAwaitingPaymentVerification: false,
    hasActiveSubscription: true,
    serverMessages: [],
    ...pageOverrides,
  };

  (window as any).waffle = {
    flag_is_active: (flag: WAFFLE_FLAG) => activeFlags.includes(flag),
  };

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  });
  await router.push('/mail');

  return mount(HeaderBar, {
    global: {
      plugins: [router, i18n],
      stubs: {
        UserMenu: true,
        BrandButton: true,
      },
    },
  });
};

describe('HeaderBar navigation links', () => {
  it('shows Dashboard and Custom Domains when ToS is accepted, subscription is active, and the flag is on', async () => {
    const wrapper = await mountHeaderBar({}, [WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP]);

    const nav = wrapper.find('nav.desktop');
    expect(nav.exists()).toBe(true);

    const links = nav.findAll('a');
    expect(links.map((link) => link.text())).toEqual(['Dashboard', 'Custom Domains']);
    expect(links.map((link) => link.attributes('href'))).toEqual(['/mail', '/custom-domains']);
  });

  it('hides the nav when the custom-domains-revamp flag is off', async () => {
    const wrapper = await mountHeaderBar({}, []);

    expect(wrapper.find('nav.desktop').exists()).toBe(false);
  });

  it('hides the nav when the user has not accepted the ToS', async () => {
    const wrapper = await mountHeaderBar(
      { needsTosAcceptance: true },
      [WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP],
    );

    expect(wrapper.find('nav.desktop').exists()).toBe(false);
  });

  it('hides the nav when the user is awaiting payment verification', async () => {
    const wrapper = await mountHeaderBar(
      { isAwaitingPaymentVerification: true },
      [WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP],
    );

    expect(wrapper.find('nav.desktop').exists()).toBe(false);
  });

  it('hides the nav when the user has no active subscription', async () => {
    const wrapper = await mountHeaderBar(
      { hasActiveSubscription: false },
      [WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP],
    );

    expect(wrapper.find('nav.desktop').exists()).toBe(false);
  });

  it('hides the nav and shows the login button for unauthenticated users', async () => {
    const wrapper = await mountHeaderBar(
      { isAuthenticated: false },
      [WAFFLE_FLAG.CUSTOM_DOMAINS_REVAMP],
    );

    expect(wrapper.find('nav.desktop').exists()).toBe(false);
    expect(wrapper.find('.login-button-link').exists()).toBe(true);
  });
});
