// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import i18n from '@/composables/i18n';
import { WAFFLE_SWITCH } from '@/types';
import TrafficBanner from './TrafficBanner.vue';

const mountTrafficBanner = (activeSwitches: WAFFLE_SWITCH[] = []) => {
  (window as any).waffle = {
    switch_is_active: (switchName: WAFFLE_SWITCH) => activeSwitches.includes(switchName),
  };

  return mount(TrafficBanner, {
    global: {
      plugins: [i18n],
    },
  });
};

describe('TrafficBanner', () => {
  it('shows the banner when the increased-traffic-banner switch is active', () => {
    const wrapper = mountTrafficBanner([WAFFLE_SWITCH.INCREASED_TRAFFIC_BANNER]);

    const banner = wrapper.find('[data-testid="traffic-banner"]');
    expect(banner.exists()).toBe(true);
    expect(banner.text()).toBe(
      "We're currently experiencing an increase in application traffic. Thank you for your patience.",
    );
  });

  it('hides the banner when the switch is inactive', () => {
    const wrapper = mountTrafficBanner([]);

    expect(wrapper.find('[data-testid="traffic-banner"]').exists()).toBe(false);
  });

  it('hides the banner when waffle is unavailable', () => {
    delete (window as any).waffle;

    const wrapper = mount(TrafficBanner, { global: { plugins: [i18n] } });

    expect(wrapper.find('[data-testid="traffic-banner"]').exists()).toBe(false);
  });
});
