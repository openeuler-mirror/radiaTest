<template>
  <div class="box-container">
    <div id="header" class="header">
      <mugen-header />
    </div>
    <n-layout id="homeBody" has-sider class="body home">
      <router-view></router-view>
    </n-layout>
  </div>
</template>
<script setup>
import { useMessage, useNotification, useDialog } from 'naive-ui';
import MugenHeader from '@/components/header/Header';
import { showFunctionMenu, workspace } from '@/assets/config/menu.js';
import { iframeLogin } from '../dashboard/modules/iframeLogin.js';

const message = useMessage();
const notification = useNotification();
const dialog = useDialog();
window.$message = message;
window.$notification = notification;
window.$dialog = dialog;

// const route = useRoute();

watchEffect(() => {
  workspace.value = 'default';
  showFunctionMenu.value = true;
  // if (route.params.workspace) {
  //   showFunctionMenu.value = true;
  //   if (route.params.workspace !== 'default' && route.params.workspace !== 'release') {
  //     workspace.value = window.atob(route.params.workspace);
  //   } else {
  //     workspace.value = route.params.workspace;
  //   }
  // } else {
  //   showFunctionMenu.value = false;
  // }
});

onMounted(() => {
  iframeLogin();
});
</script>

<style lang="less">
.box-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 1400px;
}
.home {
  width: 100%;
  height: 100%;
}
#homeBody {
  transition: all 1s ease-out;
  height: 100%;
  overflow-y: auto;
}
</style>
<style scoped>
.header {
  width: 100%;
  z-index: 5;
  height: 60px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px 0 rgb(2, 24, 42, 0.1);
  transition: height 1s ease-in-out;
  display: flex;
}

/* .body {
  position: absolute;
  padding-top: 100px;
} */
</style>
