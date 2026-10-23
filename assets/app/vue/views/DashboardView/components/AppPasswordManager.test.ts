// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import i18n from '@/composables/i18n';
import { createAppPassword, listAppPasswords, revokeAppPassword } from '../api';
import AppPasswordManager from './AppPasswordManager.vue';

vi.mock('../api', () => ({
  listAppPasswords: vi.fn(),
  createAppPassword: vi.fn(),
  revokeAppPassword: vi.fn(),
}));

const laptop = { id: 'a', name: 'Laptop', createdAt: '2026-10-23T04:44:55+00:00' };
const unnamed = { id: 'b', name: '', createdAt: null };
const MAILBOX = 'mailbox@example.org';

const listResponse = (appPasswords = [laptop, unnamed]) => ({
  success: true,
  status: 200,
  username: MAILBOX,
  appPasswords,
});

// The services-ui controls are stubbed so the tests pin this component's behaviour, not the design system's.
const ButtonStub = {
  inheritAttrs: false,
  props: ['disabled', 'formAction'],
  template: `<button :type="formAction === 'submit' ? 'submit' : 'button'" :disabled="disabled" v-bind="$attrs"><slot /></button>`,
};
const TextInputStub = {
  inheritAttrs: false,
  props: ['modelValue', 'name', 'help', 'error'],
  emits: ['update:modelValue'],
  template: `<label>
    <slot />
    <input :value="modelValue" v-bind="$attrs" @input="$emit('update:modelValue', $event.target.value)" />
    <span v-if="help">{{ help }}</span>
    <span v-if="error">{{ error }}</span>
  </label>`,
};
const PassThroughStub = { inheritAttrs: false, template: '<div v-bind="$attrs"><slot /><slot name="cta" /></div>' };
const GenericModalStub = {
  props: ['title', 'dismissible'],
  emits: ['close'],
  template: '<div data-testid="revoke-modal"><h2>{{ title }}</h2><slot /><slot name="actions" /></div>',
  methods: {
    open() {},
    close() {
      this.$emit('close');
    },
  },
};

const mountManager = async () => {
  const wrapper = mount(AppPasswordManager, {
    attachTo: document.body,
    global: {
      plugins: [i18n],
      stubs: {
        GenericModal: GenericModalStub,
        PrimaryButton: ButtonStub,
        DangerButton: ButtonStub,
        IconButton: ButtonStub,
        LinkButton: ButtonStub,
        TextInput: TextInputStub,
        NoticeBar: PassThroughStub,
        BaseBadge: PassThroughStub,
        ToolTip: PassThroughStub,
        'i18n-t': PassThroughStub,
      },
    },
  });
  await flushPromises();
  return wrapper;
};

const itemTexts = (wrapper: ReturnType<typeof mount>) =>
  wrapper.findAll('[data-testid="app-password-item"]').map((item) => item.text());

const createPassword = async (wrapper: ReturnType<typeof mount>, name: string) => {
  await wrapper.find('[data-testid="app-password-create"]').trigger('click');
  await wrapper.find('[data-testid="app-password-name-input"]').setValue(name);
  await wrapper.find('form').trigger('submit');
  await flushPromises();
};

let writeText: ReturnType<typeof vi.fn>;

beforeEach(() => {
  (window as any)._page = { userEmail: 'signin@example.com', emailAddresses: ['bootstrap@example.org'], csrfToken: 'x' };
  writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
  vi.mocked(listAppPasswords).mockResolvedValue(listResponse());
});

afterEach(() => {
  vi.clearAllMocks();
  delete (window as any)._page;
  document.body.innerHTML = '';
});

describe('AppPasswordManager', () => {
  it('lists every password from the server with a fallback name for unlabeled ones', async () => {
    const wrapper = await mountManager();

    expect(listAppPasswords).toHaveBeenCalledTimes(1);
    const items = itemTexts(wrapper);
    expect(items).toHaveLength(2);
    expect(items[0]).toContain('Laptop');
    expect(items[0]).toContain('2026');
    expect(items[1]).toContain('Unnamed app password');
    expect(wrapper.find('time').attributes('datetime')).toBe(laptop.createdAt);
    expect(wrapper.text()).toContain('Set');
    expect(wrapper.find('[data-testid="app-password-handoff"]').exists()).toBe(false);
  });

  it('shows Not set without a redundant empty-state message', async () => {
    vi.mocked(listAppPasswords).mockResolvedValue(listResponse([]));
    const wrapper = await mountManager();

    expect(wrapper.find('.app-password-empty').exists()).toBe(false);
    expect(wrapper.find('[data-testid="app-password-create"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Not set');
  });

  it('shows no status badge until the list has actually loaded', async () => {
    let resolveList: (value: unknown) => void;
    vi.mocked(listAppPasswords).mockReturnValue(new Promise((resolve) => { resolveList = resolve; }) as never);
    const wrapper = await mountManager();
    expect(wrapper.text()).not.toContain('Not set');
    expect(wrapper.text()).toContain('Loading your app passwords');

    resolveList!(listResponse([]));
    await flushPromises();
    expect(wrapper.text()).toContain('Not set');
  });

  it('keeps create, revoke and retry parked while the list is loading', async () => {
    let resolveList: (value: unknown) => void;
    vi.mocked(listAppPasswords).mockReturnValue(new Promise((resolve) => { resolveList = resolve; }) as never);
    const wrapper = await mountManager();

    expect(wrapper.find('[data-testid="app-password-create"]').attributes('disabled')).toBeDefined();

    resolveList!(listResponse());
    await flushPromises();
    expect(wrapper.find('[data-testid="app-password-create"]').attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid="app-password-revoke"]').attributes('disabled')).toBeUndefined();
  });

  it('ignores a submit while a delayed Retry of the list is still running', async () => {
    vi.mocked(listAppPasswords).mockRejectedValueOnce(new Error('offline'));
    vi.mocked(createAppPassword).mockResolvedValue({
      success: true,
      status: 200,
      appPassword: { id: 'c', name: 'Phone', createdAt: null },
      secret: 'generated-secret-value',
      username: MAILBOX,
    });
    const wrapper = await mountManager();

    await wrapper.find('[data-testid="app-password-create"]').trigger('click');
    await wrapper.find('[data-testid="app-password-name-input"]').setValue('Phone');

    let resolveList: (value: unknown) => void;
    vi.mocked(listAppPasswords).mockReturnValueOnce(new Promise((resolve) => { resolveList = resolve; }) as never);
    await wrapper.find('[data-testid="app-password-retry"]').trigger('click');

    expect(wrapper.find('[data-testid="app-password-generate"]').attributes('disabled')).toBeDefined();
    await wrapper.find('form').trigger('submit');
    await flushPromises();
    expect(createAppPassword).not.toHaveBeenCalled();

    resolveList!(listResponse());
    await flushPromises();
    await wrapper.find('form').trigger('submit');
    await flushPromises();
    expect(createAppPassword).toHaveBeenCalledWith('Phone');
    expect(itemTexts(wrapper)).toHaveLength(3);
  });

  it('shows no status badge when loading failed', async () => {
    vi.mocked(listAppPasswords).mockRejectedValueOnce(new Error('offline'));
    const wrapper = await mountManager();

    expect(wrapper.text()).not.toContain('Not set');
    expect(wrapper.text()).not.toMatch(/\bSet\b/);
  });

  it('keeps the list and offers a retry when loading fails', async () => {
    vi.mocked(listAppPasswords).mockRejectedValueOnce(new Error('offline'));
    const wrapper = await mountManager();

    expect(wrapper.text()).toContain('Could not load your app passwords.');
    expect(itemTexts(wrapper)).toHaveLength(0);

    await wrapper.find('[role="alert"] button').trigger('click');
    await flushPromises();

    expect(listAppPasswords).toHaveBeenCalledTimes(2);
    expect(itemTexts(wrapper)).toHaveLength(2);
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
  });

  it('adds a generated password to the list and hands the secret off once with the mailbox username', async () => {
    vi.mocked(createAppPassword).mockResolvedValue({
      success: true,
      status: 200,
      appPassword: { id: 'c', name: 'Phone', createdAt: '2026-10-23T05:00:00+00:00' },
      secret: 'generated-secret-value',
      username: MAILBOX,
    });
    const wrapper = await mountManager();

    await createPassword(wrapper, '  Phone  ');

    expect(createAppPassword).toHaveBeenCalledWith('Phone');
    const handoff = wrapper.find('[data-testid="app-password-handoff"]');
    expect(handoff.exists()).toBe(true);
    expect(handoff.text()).toContain('App password for Phone');
    expect(wrapper.find('[data-testid="generated-app-password"]').text()).toBe('generated-secret-value');
    // The canonical mailbox username, not the sign-in email, is what the mail client needs.
    expect(wrapper.find('[data-testid="app-password-username"]').text()).toBe(MAILBOX);
    expect(wrapper.find('form').exists()).toBe(false);
    expect(itemTexts(wrapper)).toHaveLength(3);
    expect(itemTexts(wrapper)[0]).toContain('Laptop');
    expect(itemTexts(wrapper)[2]).toContain('Phone');

    await wrapper.find('[data-testid="app-password-done"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="app-password-handoff"]').exists()).toBe(false);
    expect(wrapper.html()).not.toContain('generated-secret-value');
    expect(wrapper.find('[data-testid="app-password-create"]').exists()).toBe(true);
    expect(itemTexts(wrapper)).toHaveLength(3);
  });

  it('replaces a stale row when the server reuses its id for the new password', async () => {
    // Stalwart hands out the lowest free credential id, so a row deleted in another tab can come back as a new one.
    vi.mocked(createAppPassword).mockResolvedValue({
      success: true,
      status: 200,
      appPassword: { id: 'b', name: 'Phone', createdAt: '2026-10-23T05:00:00+00:00' },
      secret: 'generated-secret-value',
      username: MAILBOX,
    });
    const wrapper = await mountManager();

    await createPassword(wrapper, 'Phone');

    const items = itemTexts(wrapper);
    expect(items).toHaveLength(2);
    expect(items[0]).toContain('Laptop');
    expect(items[1]).toContain('Phone');
    expect(items[1]).not.toContain('Unnamed app password');
    expect(wrapper.find('[data-testid="app-password-handoff"]').text()).toContain('App password for Phone');
  });

  it('keeps the form, the typed name and the list when creation fails', async () => {
    vi.mocked(createAppPassword).mockResolvedValue({ success: false, status: 409, error: 'Quota reached' });
    const wrapper = await mountManager();

    await createPassword(wrapper, 'Tablet');

    expect(wrapper.find('[data-testid="app-password-error"]').text()).toContain('Quota reached');
    expect(wrapper.text().match(/Quota reached/g)).toHaveLength(1);
    expect((wrapper.find('[data-testid="app-password-name-input"]').element as HTMLInputElement).value).toBe('Tablet');
    expect(wrapper.find('[data-testid="app-password-handoff"]').exists()).toBe(false);
    expect(itemTexts(wrapper)).toHaveLength(2);
  });

  it('shows a generic error when the create request itself blows up', async () => {
    vi.mocked(createAppPassword).mockRejectedValue(new Error('Bad Gateway'));
    const wrapper = await mountManager();

    await createPassword(wrapper, 'Tablet');

    expect(wrapper.find('[data-testid="app-password-error"]').text()).toContain('Something went wrong');
    expect(wrapper.find('form').exists()).toBe(true);
  });

  it('reports copy success only when the clipboard write resolves', async () => {
    vi.mocked(createAppPassword).mockResolvedValue({
      success: true,
      status: 200,
      appPassword: { id: 'c', name: 'Phone', createdAt: null },
      secret: 'generated-secret-value',
      username: MAILBOX,
    });
    const wrapper = await mountManager();
    await createPassword(wrapper, 'Phone');

    await wrapper.find('[data-testid="copy-app-password"]').trigger('click');
    await flushPromises();
    expect(writeText).toHaveBeenCalledWith('generated-secret-value');
    expect(wrapper.find('[data-testid="copy-status"]').text()).toBe('Copied!');

    writeText.mockRejectedValueOnce(new Error('denied'));
    await wrapper.find('[data-testid="copy-app-password"]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="copy-status"]').text()).not.toContain('Copied');
    expect(wrapper.find('[data-testid="copy-status"]').text()).toContain('copy it yourself');
    // The secret stays on screen so the user can still save it by hand.
    expect(wrapper.find('[data-testid="generated-app-password"]').text()).toBe('generated-secret-value');
  });

  it('asks for confirmation naming the password and cancel leaves everything untouched', async () => {
    const wrapper = await mountManager();

    await wrapper.findAll('[data-testid="app-password-revoke"]')[1].trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="revoke-description"]').text()).toContain('“Unnamed app password”');
    expect(wrapper.find('[data-testid="revoke-description"]').text()).toContain('other app passwords keep working');

    await wrapper.find('[data-testid="cancel-revoke"]').trigger('click');
    await flushPromises();

    expect(revokeAppPassword).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid="revoke-description"]').exists()).toBe(false);
    expect(itemTexts(wrapper)).toHaveLength(2);
  });

  it('revokes only the confirmed password and announces it', async () => {
    vi.mocked(revokeAppPassword).mockResolvedValue({ success: true, status: 200, id: 'a' });
    const wrapper = await mountManager();

    await wrapper.findAll('[data-testid="app-password-revoke"]')[0].trigger('click');
    await wrapper.find('[data-testid="confirm-revoke"]').trigger('click');
    await flushPromises();

    expect(revokeAppPassword).toHaveBeenCalledWith('a');
    expect(itemTexts(wrapper)).toHaveLength(1);
    expect(itemTexts(wrapper)[0]).toContain('Unnamed app password');
    expect(wrapper.find('[data-testid="app-password-status"]').text()).toContain('“Laptop” was removed.');
    expect(wrapper.find('[data-testid="revoke-description"]').exists()).toBe(false);
  });

  it('treats an already-gone password as revoked only with the explicit code', async () => {
    vi.mocked(revokeAppPassword).mockResolvedValue({
      success: false,
      status: 404,
      error: 'App password not found.',
      code: 'app_password_not_found',
    });
    const wrapper = await mountManager();

    await wrapper.findAll('[data-testid="app-password-revoke"]')[0].trigger('click');
    await wrapper.find('[data-testid="confirm-revoke"]').trigger('click');
    await flushPromises();

    expect(itemTexts(wrapper)).toHaveLength(1);
    expect(wrapper.find('[data-testid="app-password-status"]').exists()).toBe(true);
  });

  it('does not claim success for an unrelated 404 such as a disabled route', async () => {
    vi.mocked(revokeAppPassword).mockResolvedValue({ success: false, status: 404, error: 'Not found' });
    const wrapper = await mountManager();

    await wrapper.findAll('[data-testid="app-password-revoke"]')[0].trigger('click');
    await wrapper.find('[data-testid="confirm-revoke"]').trigger('click');
    await flushPromises();

    expect(itemTexts(wrapper)).toHaveLength(2);
    expect(wrapper.find('[data-testid="app-password-status"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="revoke-modal"] [role="alert"]').text()).toContain('Not found');
  });

  it('parks revoking while a freshly generated secret is still on screen', async () => {
    vi.mocked(createAppPassword).mockResolvedValue({
      success: true,
      status: 200,
      appPassword: { id: 'c', name: 'Phone', createdAt: null },
      secret: 'generated-secret-value',
      username: MAILBOX,
    });
    const wrapper = await mountManager();
    expect(wrapper.find('[data-testid="app-password-revoke"]').attributes('disabled')).toBeUndefined();

    await createPassword(wrapper, 'Phone');
    for (const button of wrapper.findAll('[data-testid="app-password-revoke"]')) {
      expect(button.attributes('disabled')).toBeDefined();
    }

    await wrapper.find('[data-testid="app-password-done"]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="app-password-revoke"]').attributes('disabled')).toBeUndefined();
  });

  it('lets the backend reject a blank name and shows its message', async () => {
    vi.mocked(createAppPassword).mockResolvedValue({ success: false, status: 400, error: 'Enter a name for this app password.' });
    const wrapper = await mountManager();

    await createPassword(wrapper, '   ');

    expect(wrapper.find('form').attributes('novalidate')).toBeDefined();
    expect(createAppPassword).toHaveBeenCalledWith('');
    expect(wrapper.find('[data-testid="app-password-error"]').text()).toContain('Enter a name for this app password.');
  });

  it('keeps the password listed and shows the error when revoking fails', async () => {
    vi.mocked(revokeAppPassword).mockResolvedValue({ success: false, status: 502, error: 'Stalwart is down' });
    const wrapper = await mountManager();

    await wrapper.findAll('[data-testid="app-password-revoke"]')[0].trigger('click');
    await wrapper.find('[data-testid="confirm-revoke"]').trigger('click');
    await flushPromises();

    expect(itemTexts(wrapper)).toHaveLength(2);
    expect(wrapper.find('[data-testid="revoke-modal"] [role="alert"]').text()).toContain('Stalwart is down');
    expect(wrapper.find('[data-testid="revoke-description"]').exists()).toBe(true);
  });

  it('sends a single revoke request even when confirm is clicked twice', async () => {
    let resolveRevoke: (value: unknown) => void;
    vi.mocked(revokeAppPassword).mockReturnValue(new Promise((resolve) => { resolveRevoke = resolve; }) as never);
    const wrapper = await mountManager();

    await wrapper.findAll('[data-testid="app-password-revoke"]')[0].trigger('click');
    const confirm = wrapper.find('[data-testid="confirm-revoke"]');
    await confirm.trigger('click');
    expect(confirm.attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid="cancel-revoke"]').attributes('disabled')).toBeDefined();
    await confirm.trigger('click');

    resolveRevoke!({ success: true, status: 200, id: 'a' });
    await flushPromises();

    expect(revokeAppPassword).toHaveBeenCalledTimes(1);
    expect(itemTexts(wrapper)).toHaveLength(1);
  });
});
