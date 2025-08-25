// init localization
import { createI18n } from 'vue-i18n';
import englishL10n from '@/../l10n/en.json';


const instance = createI18n({
  locale: 'en', // We always use 'en' here because the server provides the strings
  fallbackLocale: 'en',
  messages: {
    en: englishL10n,
  }
})

export default instance;
export const i18n = instance.global;
