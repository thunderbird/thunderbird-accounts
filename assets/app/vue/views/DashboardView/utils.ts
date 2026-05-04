import type { ComposerNumberFormatting, ComposerTranslation, ComposerDateTimeFormatting } from 'vue-i18n';
import type { SubscriptionData } from './types';
import { i18n } from '@/composables/i18n';

/**
 * Converts bytes to the most appropriate unit (KB, MB, or GB) with the unit label
 * @param bytes - The number of bytes to convert
 * @returns The value with unit as a string (e.g., "30 GB", "1 KB"), formatted without unnecessary decimals
 */
export const formatBytes = (bytes: string | null): string | null => {
  if (!bytes || bytes === '0') return '0 B';

  const bytesNum = parseFloat(bytes);

  // Determine the appropriate unit
  const units = [
    { threshold: 1024 * 1024 * 1024, label: 'GB', divisor: 1024 * 1024 * 1024 },
    { threshold: 1024 * 1024, label: 'MB', divisor: 1024 * 1024 },
    { threshold: 1024, label: 'KB', divisor: 1024 },
  ];

  for (const unit of units) {
    if (bytesNum >= unit.threshold) {
      const value = bytesNum / unit.divisor;

      // Flooring the value as we don't need decimals for the UI
      const formatted = Math.floor(value);
      return `${formatted} ${unit.label}`;
    }
  }

  // If less than 1 KB, return in bytes
  return `${bytesNum} B`;
}

/**
 * Formats subscription data from the backend into a display-friendly format
 * @param subscriptionData - The subscription data from the backend
 * @param n - The number formatting function from vue-i18n
 * @param t - The translation function from vue-i18n
 * @param d - The date formatting function from vue-i18n
 * - Converts currency code to symbol
 * - Converts price from cents to dollars
 * - Converts yearly pricing to monthly equivalent
 * - Converts storage bytes to GB
 * - Removes unnecessary decimal places
 */
export const formatSubscriptionData = (
  subscriptionData: SubscriptionData,
  n: ComposerNumberFormatting,
  t: ComposerTranslation,
  d: ComposerDateTimeFormatting
): SubscriptionData => {
  // Convert price from cents to dollars
  let priceInDollars = parseFloat(subscriptionData.price) / 100;

  // Convert yearly pricing to monthly equivalent
  const period = subscriptionData.period.toLowerCase();
  if (period === 'year') {
    priceInDollars = priceInDollars / 12;
  }

  // n is not doing a good job in letting us specify the actual currency...so use javascript
  const intlN = new Intl.NumberFormat(i18n.locale.value, { style: "currency", currency: subscriptionData.currency, maximumFractionDigits: 0 });
  const formattedPrice = intlN.format(priceInDollars);

  // Format autoRenewal date if it exists
  const formattedAutoRenewal = subscriptionData.autoRenewal 
    ? d(new Date(subscriptionData.autoRenewal), 'long')
    : null;

  return {
    ...subscriptionData,
    price: formattedPrice,
    period: 'views.dashboard.yourCurrentSubscription.monthly',
    autoRenewal: formattedAutoRenewal,
    features: {
      ...subscriptionData.features,
      mailStorage: formatBytes(subscriptionData.features.mailStorage),
      sendStorage: formatBytes(subscriptionData.features.sendStorage),
    },
  };
}
