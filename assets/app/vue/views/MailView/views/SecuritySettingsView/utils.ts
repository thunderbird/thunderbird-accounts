import type { ComposerTranslation } from 'vue-i18n';

/**
 * Formats the last access date for the account activity table
 * @param date - The date to format
 * @param locale - The locale to use for formatting
 * @param t - The translation function from vue-i18n
 * @returns The formatted last access date
 */
export const formatDate = (date: Date, locale: string, t: ComposerTranslation): string => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);

  // Set yesterday's date
  yesterday.setDate(yesterday.getDate() - 1);

  const dateToCheck = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  // Format time based on current locale
  const timeString = date.toLocaleString(locale, {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  if (dateToCheck.getTime() === today.getTime()) {
    return t('views.mail.views.securitySettings.todayAt', { time: timeString });
  } else if (dateToCheck.getTime() === yesterday.getTime()) {
    return t('views.mail.views.securitySettings.yesterdayAt', { time: timeString });
  } else {
    // Format as "Jun 24, 2:15 AM" (or localized equivalent)
    const month = date.toLocaleString(locale, { month: 'short' });
    const day = date.getDate();
    return `${month} ${day}, ${timeString}`;
  }
};
