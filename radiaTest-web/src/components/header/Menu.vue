<template>
  <my-tab
    id="home"
    :has-arrow="false"
    @click="handleHomeClick"
    url="/home/dashboard"
  >
    <template #text> <n-text>主页</n-text></template>
  </my-tab>
  <my-tab url="/home/version-management" :has-arrow="false" @click="handlePvmClick">
    <template #text> <n-text>版本管理</n-text> </template>
  </my-tab>
  <my-tab
    :has-arrow="false"
    url="/home/resource-pool/management"
    @click="handlePoolClick"
  >
    <template #text> <n-text>资源池</n-text> </template>
  </my-tab>
  <my-tab url="/home/testing" :has-arrow="false" @click="handleTestClick">
    <template #text> <n-text>测试中心</n-text> </template>
  </my-tab>
  <my-tab
    id="testcase"
    :has-arrow="false"
    url="/home/tcm/folderview"
    @click="handleTcmClick"
  >
    <template #text> <n-text>用例管理</n-text> </template>
  </my-tab>
  <my-tab :has-arrow="false" url="/home/tm" @click="handleTaskClick">
    <template #text> <n-text>任务管理</n-text> </template>
  </my-tab>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';

import MyTab from './MyTab.vue';

export default defineComponent({
  components: {
    MyTab,
  },
  setup() {
    const router = useRouter();

    return {
      handlePvmClick() {
        router.push('/home/version-management');
      },
      handleTestClick() {
        router.push('/home/testing');
      },
      handleTcmClick() {
        router.push('/home/tcm/folderview');
      },
      handleTaskClick() {
        router.push('/home/tm/task');
      },
      handleHomeClick() {
        router.push('/home');
      },
      handlePoolClick() {
        if (router.currentRoute.value.name !== 'pmachine' && router.currentRoute.value !== 'vmachine') {
          router.push({ name: 'resourcePool' });
        }
      }
    };
  },
});
</script>

<style scoped></style>
