<template>
  <div>
    <div
      id="header"
      class="header"
      v-if="showHeader"
    >
      <mugen-header />
    </div>
    <n-layout
      id="main"
      has-sider
      position="absolute"
      class="body"
      :style="showHeader?{paddingTop:'115px'}:{paddingTop:'0px'}"
    >
      <n-layout-sider
        style="box-sizing: content-box;"
        bordered
        content-style="padding: 0;"
        collapse-mode="width"
        :collapsed-width="60"
        :width="300"
        :collapsed="collapsed"
        show-trigger
        @collapse="collapsed = true"
        @expand="collapsed = false"
      >
        <n-menu
          style="font-size: 20px;padding-top:20px;"
          :collapsed-width="60"
          :collapsed-icon-size="30"
          :options="menuOptions"
          :value="menuValue"
          on-model:value="value"
          on-model:expanded-keys="expandedKey"
          @update:value="handleUpdateValue"
        />
      </n-layout-sider>
      <n-layout>
        <div
          ref="container"
          class="home"
        >
          <router-view></router-view>
        </div>
      </n-layout>
    </n-layout>
  </div>
</template>
<script>
import { ref, defineComponent, provide, getCurrentInstance, watch, inject } from 'vue';
import { useNotification, useDialog, useMessage } from 'naive-ui';

import MugenHeader from '@/components/header/Header';
import { modules } from './modules/index.js';
import { storage } from '@/assets/utils/storageUtils';

export default defineComponent({
  components: {
    MugenHeader,
  },
  watch: {
    $route (newUrl) {
      this.menuOptions.forEach(item => {
        if (item.key === newUrl.name) {
          this.menuValue = newUrl.name;
        }
      });
    }
  },
  setup () {
    const { proxy } = getCurrentInstance();
    const notification = useNotification();
    const dialog = useDialog();
    const message = useMessage();
    window.$notification = notification;
    window.$dialog = dialog;
    window.$message = message;

    modules.initRoleOptions(storage?.getValue('role') || 0);
    const menuValue = ref(proxy.$root.$route.name);
    const msgCount = inject('msgCount');
    const msgCountUpdate = inject('msgCountUpdate');
    provide('showMenu', true);
    watch(msgCount, (newVal, oldVal) => {
      if (newVal > oldVal) {
        notification.info({
          content: '您有新的消息',
          duration: 1000,
        });
      }
    }, {
      deep: true,
    });
    return {
      menuValue,
      msgCount,
      msgCountUpdate,
      ...modules,
    };
  },
});
</script>
<style scoped>
* {
  margin: 0;
  padding: 0;
}

.header {
  position: fixed;
  width: 100%;
  z-index: 5;
  height: 100px;
  background-color: white;
  box-shadow: 0 2px 8px 0 rgb(2, 24, 42, 0.1);
  transition: height 1s ease-in-out;
}
@media screen and (max-width: 1423px) {
  .header {
    height: 100px;
    overflow: hidden;
  }
}
.body {
  position: absolute;
  padding-top: 115px;
}
.home {
  width: 100%;
  height: 100%;
}
#main {
  top: 0;
  transition: all 1s ease-out;
}
</style>
