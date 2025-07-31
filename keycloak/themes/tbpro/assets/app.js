import { createApp } from 'vue';
import '@thunderbirdops/services-ui/style.css';
import "@/css/main.css";
import router from '@/router.js';
import MainApp from "@/vue/App.vue";
import { createI18n } from "vue-i18n";

const i18n = createI18n({
  locale: 'en', // We always use 'en' here because the server provides the strings
  fallbackLocale: 'en',
  messages: {
    en: {},
  }
})

const app = createApp(MainApp);
app.use(router);
app.use(i18n)

// This isn't a module, so wait until the document is loaded before mounting
window.addEventListener('load', () => {
  // Load our l10n messages once the template is fully rendered.
  i18n.global.mergeLocaleMessage('en', {...window?._l10n ?? {}})
  app.mount('#app');
});

