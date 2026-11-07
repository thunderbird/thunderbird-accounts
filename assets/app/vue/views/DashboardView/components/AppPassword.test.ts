// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { shallowMount } from '@vue/test-utils';
import i18n from '@/composables/i18n';
import AppPassword from './AppPassword.vue';
import AppPasswordManager from './AppPasswordManager.vue';

vi.mock('../api', () => ({
  setAppPassword: vi.fn(),
  listAppPasswords: vi.fn(),
  createAppPassword: vi.fn(),
  revokeAppPassword: vi.fn(),
}));

const mountAppPassword = ({ generated }: { generated?: boolean }) => {
  (window as any)._page = { appPasswords: ['admin@example.org'], appPasswordIsGenerated: generated, userEmail: 'a@b.c' };

  return shallowMount(AppPassword, { global: { plugins: [i18n], renderStubDefaultSlot: true } });
};

afterEach(() => {
  delete (window as any)._page;
});

describe('AppPassword', () => {
  it('renders the named manager whenever Stalwart generates secrets', () => {
    const wrapper = mountAppPassword({ generated: true });

    expect(wrapper.find('#app-password-container').exists()).toBe(true);
    expect(wrapper.findComponent(AppPasswordManager).exists()).toBe(true);
    expect(wrapper.text()).not.toContain('Change app password');
  });

  it.each([false, undefined])('keeps the legacy flow when generated passwords are %s', (generated) => {
    const wrapper = mountAppPassword({ generated });

    expect(wrapper.findComponent(AppPasswordManager).exists()).toBe(false);
    expect(wrapper.text()).toContain('Change app password');
  });
});
