import {createApp} from "vue";
import '@thunderbirdops/services-ui/style.css';
import SelfServeForm from "@/components/SelfServeForm.vue";

// Example of creating and mounting a sfc
const selfServeForm = createApp(SelfServeForm);
selfServeForm.mount('#selfServeForm');