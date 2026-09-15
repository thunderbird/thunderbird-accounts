// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  defaultLocale,
  isStorageBlocked,
  safeGetStorageItem,
  safeRemoveStorageItem,
  safeSetStorageItem,
} from './utils';

/**
 * When the browser blocks cookies/storage (e.g. Thunderbird's "block all
 * cookies"), Firefox makes localStorage access *throw* a SecurityError
 * DOMException rather than return an empty store. defaultLocale() read storage
 * unguarded, so it threw and broke app boot with no explanation. These tests
 * pin the guarded behavior and the detection helper the UI uses to show the
 * "enable cookies" message.
 */
describe('utils storage handling', () => {
  const originalDescriptor = Object.getOwnPropertyDescriptor(
    globalThis,
    'localStorage'
  );

  /** Installs a localStorage whose getItem returns the given value. */
  function stubStorage(value: string | null) {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: { getItem: vi.fn(() => value) } as Partial<Storage>,
    });
  }

  /**
   * Installs a localStorage whose access throws, like a blocked-storage
   * browser. Firefox with "block all cookies" raises a SecurityError
   * DOMException even for a read.
   */
  function blockStorage() {
    const throwing = new DOMException(
      'The operation is insecure.',
      'SecurityError'
    );
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get() {
        throw throwing;
      },
    });
  }

  beforeEach(() => {
    Object.defineProperty(globalThis.navigator, 'language', {
      configurable: true,
      value: 'fr-FR',
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    if (originalDescriptor) {
      Object.defineProperty(globalThis, 'localStorage', originalDescriptor);
    } else {
      delete (globalThis as { localStorage?: unknown }).localStorage;
    }
  });

  describe('isStorageBlocked', () => {
    it('is false when storage is available', () => {
      stubStorage(null);
      expect(isStorageBlocked()).toBe(false);
    });

    it('is true when reading storage throws a DOMException', () => {
      blockStorage();
      expect(isStorageBlocked()).toBe(true);
    });
  });

  describe('safe storage accessors', () => {
    it('safeGetStorageItem returns the value when storage works', () => {
      stubStorage('value');
      expect(safeGetStorageItem('any')).toBe('value');
    });

    it('safeGetStorageItem returns null instead of throwing when blocked', () => {
      blockStorage();
      expect(() => safeGetStorageItem('any')).not.toThrow();
      expect(safeGetStorageItem('any')).toBeNull();
    });

    it('safeSetStorageItem does not throw when storage is blocked', () => {
      blockStorage();
      expect(() => safeSetStorageItem('k', 'v')).not.toThrow();
    });

    it('safeRemoveStorageItem does not throw when storage is blocked', () => {
      blockStorage();
      expect(() => safeRemoveStorageItem('k')).not.toThrow();
    });
  });

  describe('defaultLocale', () => {
    it('returns the stored user language when present', () => {
      stubStorage(JSON.stringify({ settings: { language: 'de' } }));
      expect(defaultLocale()).toBe('de');
    });

    it('falls back to the navigator language when no user is stored', () => {
      stubStorage(null);
      expect(defaultLocale()).toBe('fr');
    });

    it('does not throw and falls back when storage is blocked', () => {
      blockStorage();
      expect(() => defaultLocale()).not.toThrow();
      expect(defaultLocale()).toBe('fr');
    });

    it('falls back gracefully when the stored value is malformed JSON', () => {
      stubStorage('{not valid json');
      expect(() => defaultLocale()).not.toThrow();
      expect(defaultLocale()).toBe('fr');
    });
  });
});
