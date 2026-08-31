/* eslint-disable import/extensions */
import { expect, test } from 'vitest';

import { EMAIL_ALIAS_VALIDATION_MESSAGES } from './define.ts';
import { validateEmailAlias } from './emailAliasValidation.ts';

const sharedDomainOptions = {
  selectedDomain: 'example.org',
  allowedDomains: ['example.org'],
  existingCatchAlls: [],
};

test('email alias character validation rejects only the plus symbol', () => {
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'first.last' })).toBe(null);
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'first-last' })).toBe(null);
  expect(validateEmailAlias({ ...sharedDomainOptions, value: '+' })).toBe(EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL);
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'first+last' })).toBe(
    EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL
  );
});

test('email alias validation blocks catch-all aliases on domains with an existing catch-all', () => {
  expect(
    validateEmailAlias({
      value: '*',
      selectedDomain: 'example.org',
      allowedDomains: [],
      existingCatchAlls: ['@example.org'],
    })
  ).toBe(EMAIL_ALIAS_VALIDATION_MESSAGES.MIN_LENGTH);
});

test('shared domains enforce the minimum local-part length', () => {
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'ab' })).toBe(
    EMAIL_ALIAS_VALIDATION_MESSAGES.MIN_LENGTH
  );
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'abc' })).toBe(null);
});

test('custom domains allow short aliases regardless of catch-all state', () => {
  const customDomainOptions = {
    selectedDomain: 'my-domain.com',
    allowedDomains: ['example.org'],
  };

  // No catch-all set
  expect(
    validateEmailAlias({ ...customDomainOptions, value: 'ab', existingCatchAlls: [] })
  ).toBe(null);

  // Catch-all already set for this domain
  expect(
    validateEmailAlias({ ...customDomainOptions, value: 'ab', existingCatchAlls: ['@my-domain.com'] })
  ).toBe(null);
});
