import {createMemoryHistory, createRouter, RouteRecordRaw} from "vue-router";
import DashboardView from "@/views/DashboardView/index.vue";

const routes: Readonly<RouteRecordRaw[]> = [
  {
    name: 'dashboard',
    component: DashboardView,
    path: '/self-serve/',
  }
];

// create router object to export
const router = createRouter({
  history: createMemoryHistory(),
  routes,
});

export default router;
