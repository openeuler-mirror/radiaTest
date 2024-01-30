<template>
  <my-tab id="home" :has-arrow="false" @click="handleWorkbenchClick">
    <template #text>
      <div class="tab-wrap">
        <div
          class="tab-text"
          :class="{
            active: isActive('/task/') || isActive('/report/') || isActive('/distribution/'),
          }"
        >
          <n-icon :size="14"> <Dashboard /> </n-icon><n-text class="text">任务看板</n-text>
        </div>
      </div>
    </template>
  </my-tab>
  <my-tab :has-arrow="false" @click="handleDesignClick">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/design/') }">
          <n-icon :size="14"> <Server /> </n-icon><n-text class="text">测试设计</n-text>
        </div>
      </div>
    </template>
  </my-tab>
  <my-tab :has-arrow="false" @click="handlePvmClick">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/version-management/') }">
          <n-icon :size="14"> <Versions /> </n-icon><n-text class="text">版本管理</n-text>
        </div>
      </div>
    </template>
  </my-tab>
  <my-tab id="testcase" :has-arrow="false" @click="handleTcmClick">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/tcm/') }">
          <n-icon :size="14"> <Database /> </n-icon><n-text class="text">用例管理</n-text>
        </div>
      </div>
    </template>
  </my-tab>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { Dashboard } from '@vicons/carbon';
import { Server, Database } from '@vicons/fa';
import { Versions } from '@vicons/tabler';
import MyTab from './MyTab.vue';

const router = useRouter();

const isActive = (path) => {
  return router.currentRoute.value.fullPath.search(path) !== -1;
};

const handlePvmClick = () => {
  router.push({ name: 'vmProduct' });
};

const handleTcmClick = () => {
  router.push({ name: 'folderview' });
};

const handleWorkbenchClick = () => {
  router.push({ name: 'task' });
};

const handleDesignClick = () => {
  router.push({ name: 'design' });
};
</script>

<style scoped lang="less">
.tab-wrap {
  display: inline-block;
  .tab-text {
    display: flex;
    align-items: center;
    justify-content: center;

    .text {
      margin-left: 5px;
    }
  }

  .active {
    border-bottom: 3px solid rgba(0, 47, 167, 1);
  }
}
</style>
