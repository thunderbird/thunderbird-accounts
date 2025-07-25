import { createApp } from 'vue';
import '@thunderbirdops/services-ui/style.css';
import router from '@/router.js';
import MainApp from "@/vue/App.vue";

const app = createApp(MainApp);
app.use(router);

// Push the current url to the router
const path = window.location.pathname.replace(import.meta.env.VITE_BASE_PATH, '/');
router.push(path)
console.log(router.currentRoute)

// This isn't a module, so wait until the document is loaded before mounting
window.addEventListener('load', () => {
  app.mount('#app');
});