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

const mountAppPassword = ({ flagActive, generated }: { flagActive: boolean; generated: boolean }) => {
  (window as any).waffle = { flag_is_active: (flag: string) => flagActive && flag === 'app-password-management' };
  (window as any)._page = { appPasswords: ['admin@example.org'], appPasswordIsGenerated: generated, userEmail: 'a@b.c' };

  return shallowMount(AppPassword, { global: { plugins: [i18n], renderStubDefaultSlot: true } });
};

afterEach(() => {
  delete (window as any).waffle;
  delete (window as any)._page;
});

describe('AppPassword', () => {
  it('renders the named manager when the flag is on and Stalwart generates secrets', () => {
    const wrapper = mountAppPassword({ flagActive: true, generated: true });

    expect(wrapper.find('#app-password-container').exists()).toBe(true);
    expect(wrapper.findComponent(AppPasswordManager).exists()).toBe(true);
    expect(wrapper.text()).not.toContain('Change app password');
  });

  it('keeps the single replace-on-save flow while the flag is off', () => {
    const wrapper = mountAppPassword({ flagActive: false, generated: true });

    expect(wrapper.findComponent(AppPasswordManager).exists()).toBe(false);
    expect(wrapper.text()).toContain('App Password');
    expect(wrapper.text()).toContain('Change app password');
  });

  it('keeps the legacy flow on the non-JMAP admin api even with the flag on', () => {
    const wrapper = mountAppPassword({ flagActive: true, generated: false });

    expect(wrapper.findComponent(AppPasswordManager).exists()).toBe(false);
    expect(wrapper.text()).toContain('Change app password');
  });
});
