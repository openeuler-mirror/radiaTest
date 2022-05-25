<template>
  <n-config-provider
    :hljs="hljs"
    :locale="zhCN"
    :date-locale="dateZhCN"
    :theme-overrides="themeOverrides"
    :theme="theme"
    :abstract="true"
  >
    <n-dialog-provider>
      <n-loading-bar-provider>
        <n-notification-provider>
          <n-message-provider>
            <router-view v-slot="{ Component }" :class="[routerClass]">
              <transition :name="transitionName">
                <component :is="Component" />
              </transition>
              <fix-navigation v-show="notLoginPage" />
              <collapse-n-drawer
                placement="right"
                contentWidth="1200px"
                v-if="showTaskPage"
              >
                <template #content>
                  <backend-task />
                </template>
              </collapse-n-drawer>
            </router-view>
          </n-message-provider>
        </n-notification-provider>
      </n-loading-bar-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<script>
import { h, ref, getCurrentInstance, provide, readonly } from 'vue';
import { zhCN, dateZhCN } from 'naive-ui';
import hljs from 'highlight.js/lib/core';
import bash from 'highlight.js/lib/languages/bash';
import python from 'highlight.js/lib/languages/python';
import ini from 'highlight.js/lib/languages/ini';
import xml from 'highlight.js/lib/languages/xml';
import { theme } from '@/assets/config/theme.js';
import fixNavigation from '@/components/fixNavigation/fixNavgation.vue';
import collapseNDrawer from '@/components/collapseDrawer/collapseNDrawer.vue';
import backendTask from '@/views/backendTask/backendTask.vue';
import vHtml from '@/components/common/vHtml.vue';

hljs.registerLanguage('bash', bash);
hljs.registerLanguage('python', python);
hljs.registerLanguage('ini', ini);
hljs.registerLanguage('xml', xml);

const themeOverrides = {
  common: {
    primaryColor: 'rgba(0, 47, 167, 1)',
    primaryColorHover: '#3F65ABFF',
    primaryColorPressed: 'rgba(0, 47, 167, 1)',
    primaryColorSuppl: 'rgba(0, 47, 167, 1)',
  },
  Card:{
    actionColor:'rgb(242,242,242)'
  },
  DataTable: {
    thColor: 'rgb(242,242,242)'
  }
};

export default {
  name: 'App',
  components: {
    fixNavigation, collapseNDrawer, backendTask
  },
  computed: {
    notLoginPage() {
      return this.$route.name !== 'login';
    },
    showTaskPage() {
      return this.$route.name !== 'login';
    }
  },
  setup() {
    const transitionName = ref('');
    const { proxy } = getCurrentInstance();

    const msgCount = ref(0);
    provide('msgCount', readonly(msgCount));

    proxy.$newsSocket.connect();

    proxy.$newsSocket.listen('count', (data) => {
      msgCount.value = data.num;
    });
    proxy.$newsSocket.listen('notify', (msg) => {
      window.$notification.info({
        content: '通知',
        meta: () => {
          return h(vHtml, {domString: msg.content});
        },
        duration: 10000,
      });
    });

    const routerClass = ref('');
    return {
      zhCN,
      dateZhCN,
      transitionName,
      themeOverrides,
      theme,
      routerClass,
      hljs,
    };
  },
  mounted() {
    window.addEventListener('beforeunload', () => {
      if (this.$route.name === 'taskDetails') {
        sessionStorage.setItem('refresh', 1); 
      } 
    });
    window.addEventListener('load', () => {
      if (this.$route.name !== 'login' && this.$route.path) {
        if (this.$newsSocket.isConnect()) {
          this.$newsSocket.emit(
            'after connect', 
            this.$storage.getValue('token'),
          );
        }
      }
    });
  },
  watch: {
    $route(to, from) {
      if (from.name === 'login') {
        this.transitionName = 'slide-right';
        this.routerClass = 'router';
        setTimeout(() => {
          this.routerClass = '';
        }, 500);
      } else {
        this.transitionName = '';
        this.routerClass = '';
      }
    },
  },
};
</script>

<style>
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
/* 滚动槽 */
::-webkit-scrollbar-track {
  box-shadow: inset006pxrgba(0, 0, 0, 0.3);
  border-radius: 8px;
}
/* 滚动条滑块 */
::-webkit-scrollbar-thumb {
  border-radius: 8px;
  background: #abb2bf;
  box-shadow: inset006pxrgba(0, 0, 0, 0.5);
}
.n-code [class^='hljs'] {
  color: #abb2bf;
}
.n-code {
  display: block !important;
  overflow-x: scroll !important;
  padding: 1em !important;
  color: #abb2bf !important;
  background: #282c34 !important;
  padding: 3px 5px !important;
}
.bounceIn {
  animation: bounceIn;
  animation-duration: 1s;
}
.hljs {
  color: #abb2bf !important;
  background: #282c34;
}
.hljs-comment,
.hljs-quote {
  color: #5c6370 !important;
  font-style: italic !important;
}
.hljs-doctag,
.hljs-formula,
.hljs-keyword {
  color: #c678dd !important;
}
.hljs-deletion,
.hljs-name,
.hljs-section,
.hljs-selector-tag,
.hljs-subst {
  color: #e06c75 !important;
}
.hljs-literal {
  color: #56b6c2 !important;
}
.hljs-addition,
.hljs-attribute,
.hljs-meta .hljs-string,
.hljs-regexp,
.hljs-string {
  color: #98c379 !important;
}
.hljs-attr,
.hljs-number,
.hljs-selector-attr,
.hljs-selector-class,
.hljs-selector-pseudo,
.hljs-template-variable,
.hljs-type,
.hljs-variable {
  color: #d19a66 !important;
}
.hljs-bullet,
.hljs-link,
.hljs-meta,
.hljs-selector-id,
.hljs-symbol,
.hljs-title {
  color: #61aeee !important;
}
.hljs-built_in,
.hljs-class .hljs-title,
.hljs-title.class_ {
  color: #e6c07b !important;
}
.hljs-emphasis {
  font-style: italic !important;
}
.hljs-strong {
  font-weight: 700 !important;
}
.hljs-link {
  text-decoration: underline !important;
}
.slide-right-leave-active {
  opacity: 0;
  transform: translate3d(-100%, 0, 0);
}

.slide-right-enter-from {
  opacity: 0;
  transform: translate3d(100%, 0, 0);
}
span.n-avatar {
  background-color: rgba(0, 0, 0, 0);
}

html,
body {
  width: 100%;
  height: 100%;
}

#app {
  height: 100%;
}

.router {
  transition: all 0.75s ease;
}
</style>
