import { createApp } from 'vue';
import naive from 'naive-ui';
import App from './App.vue';
import store from '@/store';
import router from '@/router/index';
import axios from '@/axios';
import moment from 'moment';
import { Socket } from './socket';
import { storage } from '@/assets/utils/storageUtils';
import config from '@/assets/config/settings';

import 'vfonts/Lato.css';
import 'vfonts/FiraCode.css';
import 'animate.css';

import VMdEditor from '@kangc/v-md-editor';
import githubTheme from '@kangc/v-md-editor/lib/theme/github';
import createTodoListPlugin from '@kangc/v-md-editor/lib/plugins/todo-list/index';
// import createMermaidPlugin from '@kangc/v-md-editor/lib/plugins/mermaid/cdn'
import createTipPlugin from '@kangc/v-md-editor/lib/plugins/tip/index';
import '@kangc/v-md-editor/lib/plugins/tip/tip.css';
import '@kangc/v-md-editor/lib/style/base-editor.css';
import '@kangc/v-md-editor/lib/theme/style/github.css';
import '@kangc/v-md-editor/lib/plugins/todo-list/todo-list.css';
import '@kangc/v-md-editor/lib/plugins/mermaid/mermaid.css';

// highlightjs
import hljs from 'highlight.js';

import VueGridLayout from 'vue-grid-layout';

VMdEditor.use(githubTheme, {
  Hljs: hljs,
})
  .use(createTodoListPlugin())
  .use(createTipPlugin());

//前端应用由vue框架定义
const app = createApp(App);

//将axios模块赋予全局属性
app.config.globalProperties.$axios = axios;
app.config.globalProperties.$moment = moment;
app.config.globalProperties.$storage = storage;
app.config.globalProperties.$newsSocket = new Socket(config.newsSocketPath);

//应用插件
app
  .use(VueGridLayout)
  .use(naive)
  .use(VMdEditor)
  .use(store)
  .use(router);

//开发模式下浏览器开发者工具的启用
if (process.env.NODE_ENV === 'development') {
  //开发工具显示异常时的处理方法
  //if ('__VUE_DEVTOOLS_GLOBAL_HOOK__' in window) {
  //    window.__VUE_DEVTOOLS_GLOBAL_HOOK__.Vue = app;
  //}
  app.config.devtools = true;
} else {
  app.config.devtools = false;
}

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
