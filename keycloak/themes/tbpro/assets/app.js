import { createApp } from 'vue';
import '@thunderbirdops/services-ui/style.css';

const vueApps = [

];

for (const app of vueApps) {
  if (document.getElementById(app.id)) {
    const form = createApp(app.sfc);
    form.mount(`#${app.id}`);
  }
}

//hello world
const a = 1;

