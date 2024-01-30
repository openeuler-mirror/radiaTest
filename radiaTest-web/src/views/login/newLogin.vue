<template>
  <div class="login-page">
    <n-result status="info" title="登录" description="正在奋力登录中......"> </n-result>
  </div>
</template>
<script>
import { modules } from './modules/index';

export default {
  components: {},
  mounted() {},
  methods: {},
  setup() {
    modules.gotoHome();

    return {
      ...modules,
    };
  },
};
</script>
<style lang="less">
.login-page {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
