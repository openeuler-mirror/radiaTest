import { createApp } from 'vue';
import naive from 'naive-ui';
import App from './App.vue';
import store from '@/store';
import router from '@/router/index';
import axios from '@/axios';
import moment from 'moment';
import { storage } from '@/assets/utils/storageUtils';
import { newsSocket } from '@/assets/utils/socketUtils';

import 'vfonts/Lato.css';
import 'vfonts/FiraCode.css';
import 'animate.css';
import 'xterm/css/xterm.css';
import VueKityminder from '@orh/vue-kityminder';
import VueGridLayout from 'vue-grid-layout';
//前端应用由vue框架定义
const app = createApp(App);
//将axios模块赋予全局属性
app.config.globalProperties.$axios = axios;
app.config.globalProperties.$moment = moment;
app.config.globalProperties.$storage = storage;
app.config.globalProperties.$newsSocket = newsSocket;
//应用插件
app
  .use(VueGridLayout)
  .use(naive)
  .use(VueKityminder)
  .use(store)
  .use(router);
//开发模式下浏览器开发者工具的启用
app.config.devtools = process.env.NODE_ENV === 'development';

//将定义的应用挂载至页面根节点
app.mount('#app');

//定义全局标签页标题
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title;
  } else {
    document.title = 'radiaTest测试平台';
  }
  next();
});
