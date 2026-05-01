import { createRouter, createWebHistory } from "vue-router";
import ConsultView from "../views/ConsultView.vue";
import DraftView from "../views/DraftView.vue";
import HomeView from "../views/HomeView.vue";
import LibraryView from "../views/LibraryView.vue";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
    meta: { title: "Law Helper | 消费维权助手" },
  },
  {
    path: "/consult",
    name: "consult",
    component: ConsultView,
    meta: { title: "智能咨询 | Law Helper" },
  },
  {
    path: "/draft",
    name: "draft",
    component: DraftView,
    meta: { title: "文书生成 | Law Helper" },
  },
  {
    path: "/library",
    name: "library",
    component: LibraryView,
    meta: { title: "法规案例 | Law Helper" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.afterEach((to) => {
  document.title = to.meta.title || "Law Helper";
});

export default router;
