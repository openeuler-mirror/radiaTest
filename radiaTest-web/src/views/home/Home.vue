<template>
  <div>
    <div id="header" class="header">
      <mugen-header @menuClick="handleMenuClick" @menuBlur="handleMenuBlur" />
    </div>
    <n-layout id="main" has-sider position="absolute" class="body">
      <n-layout id="homeBody">
        <div ref="home" class="home">
          <router-view></router-view>
        </div>
      </n-layout>
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

<style scoped>
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
  padding-top: 100px;
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
