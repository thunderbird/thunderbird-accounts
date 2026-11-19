// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { KEYCLOAK_URL } from '@/defines';
import MaintenanceNotice from './MaintenanceNotice.vue';

// The tbpro login theme's defaults, as returned with no realm overrides set.
const THEME_DEFAULTS = {
  maintenanceNotice: '',
  maintenanceNoticeType: 'warning',
  maintenanceNoticeStatusUrl: '',
  maintenanceNoticeStatusText: 'Status',
};

const mountWithMessages = async (overrides: Record<string, string>) => {
  const messages = { ...THEME_DEFAULTS, ...overrides, otherKey: 'ignored' };
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => Object.entries(messages).map(([key, value]) => ({ key, value })),
  });
  vi.stubGlobal('fetch', fetchMock);

  const wrapper = mount(MaintenanceNotice);
  await flushPromises();
  return { wrapper, fetchMock };
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('MaintenanceNotice', () => {
  it('shows the notice from the tbpro login messages', async () => {
    const { wrapper, fetchMock } = await mountWithMessages({
      maintenanceNotice: '  Thundermail is down for maintenance.  ',
      maintenanceNoticeType: 'critical',
      maintenanceNoticeStatusUrl: 'https://status.example.org/',
    });

    expect(fetchMock).toHaveBeenCalledWith(`${KEYCLOAK_URL}/resources/tbpro/login/en`);
    const notice = wrapper.find('[data-testid="maintenance-notice"]');
    expect(notice.attributes('role')).toBe('status');
    expect(notice.classes()).toContain('critical');
    expect(notice.text()).toBe('Thundermail is down for maintenance. Status');
    const link = wrapper.find('[data-testid="maintenance-notice-status-url"]');
    expect(link.attributes()).toMatchObject({
      href: 'https://status.example.org/',
      target: '_blank',
      rel: 'noopener',
    });
  });

  it('shows nothing when no notice is set', async () => {
    const { wrapper } = await mountWithMessages({ maintenanceNotice: '   ' });

    expect(wrapper.find('[data-testid="maintenance-notice"]').exists()).toBe(false);
  });

  it('applies the login page rules to the type and status URL', async () => {
    const { wrapper } = await mountWithMessages({
      maintenanceNotice: 'Maintenance',
      maintenanceNoticeType: 'Critical',
      maintenanceNoticeStatusUrl: 'javascript:alert(1)',
    });

    expect(wrapper.find('[data-testid="maintenance-notice"]').classes()).toContain('warning');
    expect(wrapper.find('[data-testid="maintenance-notice-status-url"]').exists()).toBe(false);
  });

  it.each([
    ['the request fails', () => Promise.reject(new TypeError('Failed to fetch'))],
    [
      'Keycloak returns an error',
      () => Promise.resolve({ ok: false, json: async () => [{ key: 'maintenanceNotice', value: 'Maintenance' }] }),
    ],
    ['the response is not a message list', () => Promise.resolve({ ok: true, json: async () => ({}) })],
  ])('shows nothing when %s', async (_case, response) => {
    vi.stubGlobal('fetch', vi.fn(response));

    const wrapper = mount(MaintenanceNotice);
    await flushPromises();

    expect(wrapper.find('[data-testid="maintenance-notice"]').exists()).toBe(false);
  });
});
