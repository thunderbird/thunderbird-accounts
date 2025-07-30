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

// Push the current path and query to the router
const path = window.location.pathname.replace(import.meta.env.VITE_BASE_PATH, '/');
router.push([path, window.location.search].join(''));
console.log('current route: ', router.currentRoute?.value)

// Small hack to get around BrowserHistoryHelper
// https://github.com/keycloak/keycloak/blob/75ade9acef443ca98764443eb61f443b701b87dd/services/src/main/java/org/keycloak/services/resources/LoginActionsService.java#L390C51-L390C74
window.history._replaceState = window.history.replaceState;
window.history.replaceState = (state, title, url) => {
  // Call the real replaceState
  window.history._replaceState(state, title, url);
  // Update our router
  const path = url.replace(window.location.origin, '').replace(import.meta.env.VITE_BASE_PATH, '/');
  router.push([path, window.location.search].join(''));
}

// This isn't a module, so wait until the document is loaded before mounting
window.addEventListener('load', () => {
  // Load our l10n messages once the template is fully rendered.
  i18n.global.mergeLocaleMessage('en', {...window?._l10n ?? {}})
  app.mount('#app');
});

