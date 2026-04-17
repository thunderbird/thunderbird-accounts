import { createApp } from 'vue';
import '@thunderbirdops/services-ui/style.css';

import App from '@/App.vue';
import i18n from '@/composables/i18n';
import router from '@/router';
import { createPinia } from 'pinia';

const app = createApp(App);

app.use(i18n);
app.use(router);
app.use(createPinia());
app.mount('#app');
