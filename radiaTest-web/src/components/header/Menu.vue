<template>
  <my-tab
    id="home"
    :has-arrow="false"
    @click="handleHomeClick"
    url="/home/dashboard"
  >
    <template #text> 主页</template>
  </my-tab>
  <my-tab url="/home/pvm">
    <template #text> 版本管理 </template>
    <template #menu>
      <animate-button url="/home/pvm/product" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <logo-firebase />
          </n-icon>
        </template>
        <template #text> 产品版本 </template>
      </animate-button>
      <animate-button url="/home/pvm/milestone" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <task-list />
          </n-icon>
        </template>
        <template #text> 里程碑 </template>
      </animate-button>
    </template>
  </my-tab>
  <my-tab url="/home/resource-pool">
    <template #text> 资源池 </template>
    <template #menu>
      <animate-button url="/home/resource-pool/pmachine" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <computer-round />
          </n-icon>
        </template>
        <template #text> 物理机 </template>
      </animate-button>
      <animate-button url="/home/resource-pool/vmachine" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <computer-round />
          </n-icon>
        </template>
        <template #text> 虚拟机 </template>
      </animate-button>
      <animate-button
        :disabled="true"
        url="/home/resource-pool/docker"
        :size="270"
      >
        <template #icon>
          <n-icon class="icon" size="160">
            <logo-docker />
          </n-icon>
        </template>
        <template #text> Docker </template>
      </animate-button>
    </template>
  </my-tab>
  <my-tab url="/home/testing">
    <template #text> 测试中心 </template>
    <template #menu>
      <animate-button url="/home/testing/jobs" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <board />
          </n-icon>
        </template>
        <template #text> 测试看板 </template>
      </animate-button>
      <animate-button url="/home/testing/template" :size="270">
        <template #icon>
          <n-icon class="icon" size="160">
            <format />
          </n-icon>
        </template>
        <template #text> 模板仓库 </template>
      </animate-button>
    </template>
  </my-tab>
  <my-tab
    id="testcase"
    :has-arrow="false"
    url="/home/tcm/testcase"
    @click="handleTcmClick"
  >
    <template #text> 用例管理 </template>
  </my-tab>
  <my-tab :has-arrow="false" url="/home/tm" @click="handleTaskClick">
    <template #text> 任务管理 </template>
  </my-tab>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';
import {
  ComputerRound,
  FormatIndentIncreaseRound as Format,
} from '@vicons/material';
import {
  TaskListRtl20Filled as TaskList,
  Board20Filled as Board,
} from '@vicons/fluent';
import { LogoFirebase, LogoDocker } from '@vicons/ionicons5';

import MyTab from './MyTab.vue';
import AnimateButton from '@/components/public/AnimateButton';

export default defineComponent({
  components: {
    MyTab,
    AnimateButton,
    ComputerRound,
    LogoFirebase,
    LogoDocker,
    TaskList,
    Board,
    Format,
  },
  setup() {
    const router = useRouter();

    return {
      handleTcmClick() {
        router.push('/home/tcm/');
      },
      handleTaskClick() {
        router.push('/home/tm/task');
      },
      handleHomeClick() {
        router.push('/home');
      },
    };
  },
});
</script>

<style scoped></style>
