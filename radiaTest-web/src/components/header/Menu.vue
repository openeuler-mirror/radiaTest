<template>
  <my-tab id="home" :has-arrow="false" @click="handleWorkbenchClick">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/workbench/') }">
          <n-icon :size="14"> <Dashboard /> </n-icon><n-text class="text">工作台</n-text>
        </div>
      </div>
    </template>
  </my-tab>
  <my-tab :has-arrow="false" @click="handlePoolClick" v-if="showResourcePool">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/resource-pool/') }">
          <n-icon :size="14"> <Server /> </n-icon><n-text class="text">资源池</n-text>
        </div>
      </div>
    </template>
  </my-tab>
  <my-tab :has-arrow="false" @click="handlePvmClick" v-if="showVersionManagment">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/version-management/') }">
          <n-icon :size="14"> <Versions /> </n-icon><n-text class="text">版本管理</n-text>
        </div>
      </div>
    </template>
  </my-tab>
  <my-tab id="testcase" :has-arrow="false" @click="handleTcmClick" v-if="showCaseManagment">
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
import { useRouter, useRoute } from 'vue-router';
import { Dashboard } from '@vicons/carbon';
import { Server, Database } from '@vicons/fa';
import { Versions } from '@vicons/tabler';
import MyTab from './MyTab.vue';

const router = useRouter();
const route = useRoute();

const showResourcePool = computed(() => {
  if (window.atob(route.params?.workspace).search('group') !== -1) {
    return false;
  }
  return true;
});

const showVersionManagment = computed(() => {
  if (window.atob(route.params?.workspace).search('group') !== -1) {
    return false;
  }
  return true;
});

const showCaseManagment = computed(() => {
  if (window.atob(route.params?.workspace).search('group') !== -1) {
    return false;
  }
  return true;
});

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
  router.push({ name: 'dashboard' });
};

const handlePoolClick = () => {
  if (router.currentRoute.value.name !== 'pmachine' && router.currentRoute.value.name !== 'vmachine') {
    router.push({ name: 'resourcePool' });
  }
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
