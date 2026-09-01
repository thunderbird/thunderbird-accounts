import { WAFFLE_FLAG, WAFFLE_SWITCH } from '@/types';

// Check if we already have a local user preferred language
// Otherwise just use the navigators language.
export const defaultLocale = () => {
  const user = JSON.parse(localStorage?.getItem('tba/user') ?? '{}');
  return user?.settings?.language ?? navigator.language.split('-')[0];
};

export const isWaffleFlagActive = (flag: WAFFLE_FLAG): boolean =>
  Boolean((window as any).waffle?.flag_is_active(flag));

export const isWaffleSwitchActive = (switchName: WAFFLE_SWITCH): boolean =>
  Boolean((window as any).waffle?.switch_is_active(switchName));

