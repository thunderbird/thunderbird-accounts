import type { ComposerNumberFormatting, ComposerTranslation, ComposerDateTimeFormatting } from 'vue-i18n';
import type { SubscriptionData } from './types';
import { i18n } from '@/composables/i18n';
import { dinero, toDecimal, allocate } from 'dinero.js';
import * as currencies from 'dinero.js/currencies';
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
 * Takes in the amount in cents (raw data from Paddle), currency code and billingInterval and outputs the correctly formatted price in monthly interval.
 * Ex/
 *  * (12_000, CAD, year) = CA$10
 *  * (12_000, USD, year) = $10
 *  * (11_700, JPY, year) = ¥975
 */
export const formatLocalizedMonthlyPrice = (
  amountCents: number,
  currency: string,
  billingInterval: string | undefined
): string => {
  // Use currency if supported, otherwise fallback to USD.
  const currencyType = currency in currencies ? currencies[currency as keyof typeof currencies] : currencies['USD'];
  const annualBilling = billingInterval?.toLowerCase() === 'year';

  const priceObj = dinero({ amount: amountCents, currency: currencyType });

  // allocate expects a list of equal amounts, so in order to split this by 12 correctly we must fill a list 12 times...bleh  
  const allocation = Array(12).fill(0, 0, 12).map(() => (1.0 / 12.0) * 100.0);
  const price = annualBilling ? toDecimal(allocate(priceObj, allocation)[0]) : toDecimal(priceObj);

  return new Intl.NumberFormat(i18n.locale.value, {
    style: 'currency',
    currency,
    // @ts-ignore: lsp is complaining this property doesn't exist, so ignore that "error".
    trailingZeroDisplay: 'stripIfInteger' 
  }).format(parseFloat(price));
};

/**
 * Formats subscription data from the backend into a display-friendly format
 * @param subscriptionData - The subscription data from the backend
 * @param n - The number formatting function from vue-i18n (not used)
 * @param t - The translation function from vue-i18n (not used)
 * @param d - The date formatting function from vue-i18n
 * - Converts currency code to symbol
 * - Converts price from cents to dollars
 * - Converts yearly pricing to monthly equivalent
 * - Converts storage bytes to GB
 * - Removes unnecessary decimal places
 */
export const formatSubscriptionData = (
  subscriptionData: SubscriptionData,
  _n: ComposerNumberFormatting,
  _t: ComposerTranslation,
  d: ComposerDateTimeFormatting
): SubscriptionData => {
  const formattedPrice = formatLocalizedMonthlyPrice(parseInt(subscriptionData.price, 10), subscriptionData.currency, subscriptionData.period);

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
