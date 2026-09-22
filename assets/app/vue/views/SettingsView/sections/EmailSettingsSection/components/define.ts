export const EMAIL_ALIAS_MIN_LENGTH = 3;
export const EMAIL_ALIAS_MAX_LENGTH = 40;
export const EMAIL_ALIAS_FORBIDDEN_SYMBOLS = ['+'] as const;

export const EMAIL_ALIAS_VALIDATION_MESSAGES = {
  MIN_LENGTH: 'views.mail.sections.emailSettings.nameValidationErrorMinLength',
  MAX_LENGTH: 'views.mail.sections.emailSettings.nameValidationErrorMaxLength',
  PLUS_SYMBOL: 'views.mail.sections.emailSettings.nameValidationErrorPlusSymbol',
} as const;

export type EmailAliasValidationMessageKey =
  (typeof EMAIL_ALIAS_VALIDATION_MESSAGES)[keyof typeof EMAIL_ALIAS_VALIDATION_MESSAGES];
