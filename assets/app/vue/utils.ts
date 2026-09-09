import { WAFFLE_FLAG, WAFFLE_SWITCH } from '@/types';

/**
 * Accessing localStorage/sessionStorage throws (rather than returning an empty
 * store) when the browser is set to block cookies/storage — e.g. Thunderbird's
 * "block all cookies". Firefox raises a SecurityError DOMException
 * ("The operation is insecure.") even for a read. Thundermail keeps the session
 * in a cookie, so a user in this state cannot authenticate; we detect it here so
 * the UI can tell them to enable cookies instead of failing silently.
 */
export const isStorageBlocked = (): boolean => {
  try {
    // A read is enough to trigger the DOMException when storage is blocked.
    // The key is arbitrary and never written; we only care whether access
    // throws.
    void localStorage?.getItem('tba/storage-probe');
    return false;
  } catch {
    return true;
  }
};

/**
 * Read from localStorage without ever throwing. When storage is blocked, even
 * `typeof localStorage` and optional chaining do not help: the `window
 * .localStorage` *getter itself* throws SecurityError, so every access must be
 * wrapped. Returns null when storage is unavailable or the key is missing.
 */
export const safeGetStorageItem = (key: string): string | null => {
  try {
    return localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
};

/** Write to localStorage without ever throwing (no-op when storage is blocked). */
export const safeSetStorageItem = (key: string, value: string): void => {
  try {
    localStorage?.setItem(key, value);
  } catch {
    // Storage blocked: nothing we can do, and this must never break the caller.
  }
};

/** Remove from localStorage without ever throwing (no-op when storage is blocked). */
export const safeRemoveStorageItem = (key: string): void => {
  try {
    localStorage?.removeItem(key);
  } catch {
    // Storage blocked: nothing we can do, and this must never break the caller.
  }
};

// Check if we already have a local user preferred language
// Otherwise just use the navigators language.
export const defaultLocale = () => {
  let user: { settings?: { language?: string } } = {};
  try {
    user = JSON.parse(safeGetStorageItem('tba/user') ?? '{}');
  } catch {
    // Malformed value: fall back to the navigator language. Storage-blocked
    // reads are already swallowed by safeGetStorageItem; isStorageBlocked()
    // surfaces the cookies-disabled message separately, so we must not let this
    // throw and break app boot.
  }
  return user?.settings?.language ?? navigator.language.split('-')[0];
};

export const isWaffleFlagActive = (flag: WAFFLE_FLAG): boolean =>
  Boolean((window as any).waffle?.flag_is_active?.(flag));

export const isWaffleSwitchActive = (switchName: WAFFLE_SWITCH): boolean =>
  Boolean((window as any).waffle?.switch_is_active?.(switchName));
