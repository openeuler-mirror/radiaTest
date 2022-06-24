<template>
  <my-tab
    id="home"
    :has-arrow="false"
    @click="handleHomeClick"
    url="/home/dashboard"
  >
    <template #text> <n-text>主页</n-text></template>
  </my-tab>
  <my-tab url="/home/pvm">
    <template #text> <n-text>版本管理</n-text> </template>
    <template #menu>
      <animate-button url="/home/pvm/product" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <logo-firebase />
          </n-icon>
        </template>
        <template #text><n-text>产品版本</n-text> </template>
      </animate-button>
      <animate-button url="/home/pvm/milestone" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <task-list />
          </n-icon>
        </template>
        <template #text> <n-text>里程碑</n-text> </template>
      </animate-button>
    </template>
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
import {
  TaskListRtl20Filled as TaskList,
} from '@vicons/fluent';
import { LogoFirebase } from '@vicons/ionicons5';

import MyTab from './MyTab.vue';
import AnimateButton from '@/components/public/AnimateButton';

export default defineComponent({
  components: {
    MyTab,
    AnimateButton,
    LogoFirebase,
    TaskList,
  },
  setup() {
    const router = useRouter();

    return {
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
