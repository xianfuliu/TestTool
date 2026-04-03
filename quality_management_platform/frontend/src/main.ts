import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "@/app/App.vue";
import router from "@/app/router";
import "@/app/styles/global.css";

createApp(App).use(router).use(ElementPlus).mount("#app");
