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
  const isCatchAllRequest = !value || value === '*';

  if (EMAIL_ALIAS_FORBIDDEN_SYMBOLS.some((symbol) => value.includes(symbol))) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL;
  }

  if (isCatchAllRequest) {
    return isSharedDomain || isUsedCatchAll ? EMAIL_ALIAS_VALIDATION_MESSAGES.MIN_LENGTH : null;
  }

  if (isSharedDomain && value.length < EMAIL_ALIAS_MIN_LENGTH) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.MIN_LENGTH;
  }

  if (value.length > EMAIL_ALIAS_MAX_LENGTH) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.MAX_LENGTH;
  }

  return null;
};
