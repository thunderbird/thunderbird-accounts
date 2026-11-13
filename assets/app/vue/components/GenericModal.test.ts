// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import i18n from '@/composables/i18n';
import GenericModal from './GenericModal.vue';

const mountModal = (props: Record<string, unknown> = {}) =>
  mount(GenericModal, {
    props: { title: 'Test dialog', ...props },
    slots: { default: '<p>Body</p>' },
    global: { plugins: [i18n] },
    attachTo: document.body,
  });

afterEach(() => {
  document.body.innerHTML = '';
});

describe('GenericModal', () => {
  it('names the dialog after its title for assistive technology', () => {
    const wrapper = mountModal();
    const dialog = wrapper.find('dialog');
    const heading = wrapper.find('h2');

    expect(heading.text()).toBe('Test dialog');
    expect(heading.attributes('id')).toBeTruthy();
    expect(dialog.attributes('aria-labelledby')).toBe(heading.attributes('id'));
  });

  it('emits close for the close button, programmatic close and Escape', async () => {
    const wrapper = mountModal();
    const dialog = wrapper.find('dialog').element as HTMLDialogElement;
    // happy-dom may lack the dialog API; emulate the browser's close() -> close event contract.
    dialog.close = () => {
      dialog.removeAttribute('open');
      dialog.dispatchEvent(new Event('close'));
    };

    await wrapper.find('button.close-button').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);

    (wrapper.vm as unknown as { close: () => void }).close();
    expect(wrapper.emitted('close')).toHaveLength(2);

    // Escape: the browser fires cancel, then close.
    const cancel = new Event('cancel', { cancelable: true });
    dialog.dispatchEvent(cancel);
    expect(cancel.defaultPrevented).toBe(false);
    dialog.dispatchEvent(new Event('close'));
    expect(wrapper.emitted('close')).toHaveLength(3);
  });

  it('hides the close button and swallows Escape while not dismissible', async () => {
    const wrapper = mountModal({ dismissible: false });
    const dialog = wrapper.find('dialog').element as HTMLDialogElement;

    expect(wrapper.find('button.close-button').exists()).toBe(false);

    const cancel = new Event('cancel', { cancelable: true });
    dialog.dispatchEvent(cancel);
    expect(cancel.defaultPrevented).toBe(true);

    await wrapper.setProps({ dismissible: true });
    expect(wrapper.find('button.close-button').exists()).toBe(true);
  });
});
