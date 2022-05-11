<template>
  <div class="box">
    <n-tabs type="line" animated @update:value="tabChanges">
      <n-tab-pane name="product" tab="产品版本">
      </n-tab-pane>
      <n-tab-pane name="milestone" tab="里程碑">
      </n-tab-pane>
    </n-tabs>
    <router-view />
  </div>
</template>
<script>
import router from '@/router';
export default {
  methods:{
    tabChanges(value){
      router.push({name:value});
    }
  }
};
</script>
<style lang="less" scoped>
.box {
  height: 100%;
  width: 100%;
  padding: 20px 20px;
}
</style>
