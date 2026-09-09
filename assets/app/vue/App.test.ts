// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createMemoryHistory, createRouter } from 'vue-router';
import i18n from '@/composables/i18n';
import App from './App.vue';

const mockIsStorageBlocked = vi.fn();

vi.mock('@/utils', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/utils')>();
  return { ...actual, isStorageBlocked: () => mockIsStorageBlocked() };
});

// The app template pulls in HeaderBar/FooterBar/TrafficBanner, which read
// window._page and waffle; stub them so this test focuses on the cookie notice.
vi.mock('@/components/HeaderBar.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/components/FooterBar.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/components/TrafficBanner.vue', () => ({ default: { template: '<div />' } }));

// Stub the services-ui NoticeBar to a plain slot wrapper: the real component's
// internals are out of scope here, we only assert our own notice is rendered.
vi.mock('@thunderbirdops/services-ui', () => ({
  NoticeBar: {
    props: ['type'],
    template: '<div><slot /></div>',
  },
  NoticeBarTypes: { Critical: 'critical', Success: 'success', Warning: 'warning', Info: 'info' },
}));

const mountApp = async () => {
  window._page = {
    isAuthenticated: false,
    userDisplayName: '',
    needsTosAcceptance: false,
    isAwaitingPaymentVerification: false,
    hasActiveSubscription: false,
    serverMessages: [],
  } as Window['_page'];

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'home', component: { template: '<div />' } }],
  });
  router.push('/');
  await router.isReady();

  const wrapper = mount(App, { global: { plugins: [router, i18n] } });
  await wrapper.vm.$nextTick();
  return wrapper;
};

describe('App.vue cookies-disabled notice', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('shows the enable-cookies notice when storage is blocked', async () => {
    mockIsStorageBlocked.mockReturnValue(true);
    const wrapper = await mountApp();

    const notice = wrapper.find('[data-testid="cookies-disabled-notice"]');
    expect(notice.exists()).toBe(true);
    // Assert the localized message renders without coupling to exact wording.
    expect(notice.text()).toBe(i18n.global.t('cookiesDisabled.message'));
    expect(notice.text().length).toBeGreaterThan(0);
  });

  it('does not show the notice when storage is available', async () => {
    mockIsStorageBlocked.mockReturnValue(false);
    const wrapper = await mountApp();

    expect(
      wrapper.find('[data-testid="cookies-disabled-notice"]').exists()
    ).toBe(false);
  });
});
