<template>
  <div class="box-container">
    <div id="header" class="header">
      <mugen-header @menuClick="handleMenuClick" @menuBlur="handleMenuBlur" />
    </div>
    <n-layout id="homeBody" has-sider class="body home">
      <router-view></router-view>
    </n-layout>
  </div>
</template>
<script>
import { ref, defineComponent } from 'vue';
import { useMessage, useNotification, useDialog } from 'naive-ui';
import MugenHeader from '@/components/header/Header';
import modules from './index';

export default defineComponent({
  components: {
    MugenHeader,
  },
  setup() {
    const message = useMessage();
    const notification = useNotification();
    const dialog = useDialog();
    window.$message = message;
    window.$notification = notification;
    window.$dialog = dialog;

    const home = ref(null);

    return {
      home,
      ...modules,
    };
  },
});
</script>

<style>
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
  height: 100px;
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
