// init localization
import { createI18n } from 'vue-i18n';

const instance = createI18n({
  locale: 'en', // We always use 'en' here because the server provides the strings
  fallbackLocale: 'en',
  messages: {
    en: {},
  }
})

export default instance;
export const i18n = instance.global;
