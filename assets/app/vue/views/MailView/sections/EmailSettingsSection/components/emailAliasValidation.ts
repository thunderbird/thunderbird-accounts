import {
  EMAIL_ALIAS_FORBIDDEN_SYMBOLS,
  EMAIL_ALIAS_MAX_LENGTH,
  EMAIL_ALIAS_MIN_LENGTH,
  EMAIL_ALIAS_VALIDATION_MESSAGES,
  type EmailAliasValidationMessageKey,
} from './define';

type EmailAliasValidationOptions = {
  value: string;
  selectedDomain: string | null;
  allowedDomains: string[];
  existingCatchAlls: string[];
};

/**
 * Allows catch-all aliases on unused custom domains and otherwise validates
 * email alias local parts for length and disallowed symbols.
 */
export const validateEmailAlias = ({
  value,
  selectedDomain,
  allowedDomains,
  existingCatchAlls,
}: EmailAliasValidationOptions): EmailAliasValidationMessageKey | null => {
  const isSharedDomain = allowedDomains.includes(selectedDomain);
  const isUsedCatchAll = existingCatchAlls.some((catchAll) => catchAll.endsWith(`@${selectedDomain}`));

  if (EMAIL_ALIAS_FORBIDDEN_SYMBOLS.some((symbol) => value.includes(symbol))) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL;
  }

  // If we're a shared domain or a domain that already has a catch all we'll want to error out on min length.
  if ((isUsedCatchAll || isSharedDomain) && (!value || value.length < EMAIL_ALIAS_MIN_LENGTH)) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.MIN_LENGTH;
  }

  // Catch-all domain for #446
  if (!isUsedCatchAll && (!value || value === '*')) {
    return null;
  }

  if (value.length > EMAIL_ALIAS_MAX_LENGTH) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.MAX_LENGTH;
  }

  return null;
};
