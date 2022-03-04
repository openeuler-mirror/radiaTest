<template>
  <div class="box-container">
    <div id="header" class="header" v-if="showHeader">
      <mugen-header />
    </div>
    <n-layout has-sider class="body">
      <n-layout-sider
        style="box-sizing: content-box"
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
          style="font-size: 20px; padding-top: 20px"
          :collapsed-width="60"
          :collapsed-icon-size="30"
          :options="menuOptions"
          :value="menuValue"
          on-model:value="value"
          on-model:expanded-keys="expandedKey"
          @update:value="handleUpdateValue"
        />
      </n-layout-sider>
      <n-layout id="homeBody">
        <div ref="container" class="home">
          <div
            v-if="!showHeader"
            style="
              display: flex;
              padding-right: 20px;
              justify-content: flex-end;
              height: 50px;
              line-height: 50px;
            "
          >
            <n-button text type="primary" @click="logout">
              <template #icon>
                <n-icon>
                  <exit />
                </n-icon>
              </template>
              退出登录
            </n-button>
          </div>
          <router-view></router-view>
        </div>
      </n-layout>
    </n-layout>
  </div>
</template>
<script>
import { ref, defineComponent, provide, getCurrentInstance, watch, inject } from 'vue';
import { useNotification, useDialog, useMessage } from 'naive-ui';
import { Exit } from '@vicons/ionicons5';

import MugenHeader from '@/components/header/Header';
import { modules } from './modules/index.js';
import { storage } from '@/assets/utils/storageUtils';

export default defineComponent({
  components: {
    MugenHeader, Exit
  },
  watch: {
    $route(newUrl) {
      this.menuOptions.forEach(item => {
        if (newUrl.path.indexOf(item.key) !== -1) {
          this.menuValue = item.key;
        }
      });
    }
  },
  setup() {
    const { proxy } = getCurrentInstance();
    const notification = useNotification();
    const dialog = useDialog();
    const message = useMessage();
    window.$notification = notification;
    window.$dialog = dialog;
    window.$message = message;

    modules.initRoleOptions(storage?.getValue('role') || 0);
    const menuValue = ref(proxy.$root.$route.name);
    modules.menuOptions.value.forEach(item => {
      if (proxy.$root.$route.path.indexOf(item.key) !== -1) {
        menuValue.value = item.key;
      }
    });
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
  width: 100%;
  z-index: 5;
  height: 100px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px 0 rgb(2, 24, 42, 0.1);
  transition: height 1s ease-in-out;
}
@media screen and (max-width: 1423px) {
  .header {
    height: 100px;
    overflow: hidden;
  }
}
</style>
