import type { ComposerNumberFormatting, ComposerTranslation, ComposerDateTimeFormatting } from 'vue-i18n';
import type { SubscriptionData } from './types';

export const getCurrencySymbol = (currency: string, n: ComposerNumberFormatting) => {
  const formatted = n(0, {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
  });

  return formatted.replace(/[\d\s.,]/g, '');
}

/**
 * Converts bytes to the most appropriate unit (KB, MB, or GB) with the unit label
 * @param bytes - The number of bytes to convert
 * @returns The value with unit as a string (e.g., "30 GB", "1 KB"), formatted without unnecessary decimals
 */
const formatBytes = (bytes: string | null): string | null => {
  if (!bytes) return null;

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

      // Format without unnecessary decimals
      const formatted = value % 1 === 0 ? value.toFixed(0) : value.toFixed(2);
      return `${formatted} ${unit.label}`;
    }
  }

  // If less than 1 KB, return in bytes
  return `${bytesNum} bytes`;
}

/**
 * Formats subscription data from the backend into a display-friendly format
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
  const currencySymbol = getCurrencySymbol(subscriptionData.currency, n);

  // Convert price from cents to dollars
  let priceInDollars = parseFloat(subscriptionData.price) / 100;

  // Convert yearly pricing to monthly equivalent
  const period = subscriptionData.period.toLowerCase();
  if (period === 'year') {
    priceInDollars = priceInDollars / 12;
  }

  // Format price without unnecessary decimals (9 instead of 9.00)
  const formattedPrice = priceInDollars % 1 === 0 
    ? priceInDollars.toFixed(0) 
    : priceInDollars.toFixed(2);

  // Format autoRenewal date if it exists
  const formattedAutoRenewal = subscriptionData.autoRenewal 
    ? d(new Date(subscriptionData.autoRenewal), 'long')
    : null;

  return {
    ...subscriptionData,
    currency: currencySymbol,
    price: formattedPrice,
    period: t('views.dashboard.yourCurrentSubscription.monthly'),
    autoRenewal: formattedAutoRenewal,
    features: {
      ...subscriptionData.features,
      mailStorage: formatBytes(subscriptionData.features.mailStorage),
      sendStorage: formatBytes(subscriptionData.features.sendStorage),
    },
  };
}
