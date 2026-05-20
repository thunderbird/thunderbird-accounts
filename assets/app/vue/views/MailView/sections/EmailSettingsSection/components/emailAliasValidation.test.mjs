/* eslint-disable import/extensions */
import { expect, test } from 'vitest';

import {
  EMAIL_ALIAS_VALIDATION_MESSAGES,
  validateEmailAlias,
} from './emailAliasValidation.ts';

const sharedDomainOptions = {
  selectedDomain: 'example.org',
  allowedDomains: ['example.org'],
  existingCatchAlls: [],
};

test('email alias character validation rejects only the plus symbol', () => {
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'first.last' })).toBe(null);
  expect(validateEmailAlias({ ...sharedDomainOptions, value: 'first-last' })).toBe(null);
  expect(
    validateEmailAlias({ ...sharedDomainOptions, value: '+' }),
  ).toBe(EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL);
  expect(
    validateEmailAlias({ ...sharedDomainOptions, value: 'first+last' }),
  ).toBe(EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL);
});
