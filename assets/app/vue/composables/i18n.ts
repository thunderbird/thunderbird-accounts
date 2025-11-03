// init localization
import { createI18n } from 'vue-i18n';
import { defaultLocale } from '@/utils';

// language source files
import en from '@/locales/en.json';

const messages = {
  en, // English
};

const datetimeFormats = {
  en: {
    long: {
      year: 'numeric' as const,
      month: 'long' as const,
      day: 'numeric' as const,
    },
  },
};

const numberFormats = {
  en: {
    currency: {
      style: 'currency' as const,
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    },
  },
};

const instance = createI18n({
  legacy: false,
  globalInjection: true,
  locale: defaultLocale(),
  fallbackLocale: 'en',
  messages,
  datetimeFormats,
  numberFormats,
});

export default instance;
export const i18n = instance.global;
export type i18nType = typeof i18n.t;
