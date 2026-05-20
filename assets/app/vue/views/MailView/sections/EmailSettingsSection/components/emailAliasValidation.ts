export const EMAIL_ALIAS_VALIDATION_MESSAGES = {
  MIN_LENGTH: 'views.mail.sections.emailSettings.nameValidationErrorMinLength',
  MAX_LENGTH: 'views.mail.sections.emailSettings.nameValidationErrorMaxLength',
  PLUS_SYMBOL: 'views.mail.sections.emailSettings.nameValidationErrorPlusSymbol',
} as const;

export type EmailAliasValidationMessageKey =
  (typeof EMAIL_ALIAS_VALIDATION_MESSAGES)[keyof typeof EMAIL_ALIAS_VALIDATION_MESSAGES];

type EmailAliasValidationOptions = {
  value: string;
  selectedDomain: string | null;
  allowedDomains: string[];
  existingCatchAlls: string[];
};

export const validateEmailAlias = ({
  value,
  selectedDomain,
  allowedDomains,
  existingCatchAlls,
}: EmailAliasValidationOptions): EmailAliasValidationMessageKey | null => {
  const isSharedDomain = allowedDomains.includes(selectedDomain);
  const isUsedCatchAll = existingCatchAlls.includes(`@${selectedDomain}`);

  if (value.includes('+')) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.PLUS_SYMBOL;
  }

  // If we're a shared domain or a domain that already has a catch all we'll want to error out on min length.
  if ((isUsedCatchAll || isSharedDomain) && (!value || value.length < 3)) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.MIN_LENGTH;
  }

  // Catch-all domain for #446
  if (!isUsedCatchAll && (!value || value === '*')) {
    return null;
  }

  if (value.length > 40) {
    return EMAIL_ALIAS_VALIDATION_MESSAGES.MAX_LENGTH;
  }

  return null;
};
