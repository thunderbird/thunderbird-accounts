// init localization
import { createI18n } from 'vue-i18n';
import { defaultLocale } from '@/utils';

// language source files
import en from '@/locales/en.json';

const messages = {
  en, // English
};

const instance = createI18n({
  legacy: false,
  globalInjection: true,
  locale: defaultLocale(),
  fallbackLocale: 'en',
  messages,
});

export default instance;
export const i18n = instance.global;
export type i18nType = typeof i18n.t;
