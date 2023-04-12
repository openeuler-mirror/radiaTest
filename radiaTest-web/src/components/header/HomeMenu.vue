<template>
  <my-tab id="homeMenu" :has-arrow="false" @click="handleHomeMenuClick">
    <template #text>
      <div class="tab-wrap">
        <div class="tab-text" :class="{ active: isActive('/home/workspaces') }">
          <n-icon :size="20"> <Home /> </n-icon><n-text class="text">首页</n-text>
        </div>
      </div>
    </template>
  </my-tab>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { Home } from '@vicons/carbon';

const router = useRouter();

const handleHomeMenuClick = () => {
  router.push('/home/workspaces');
};

const isActive = (path) => {
  return router.currentRoute.value.fullPath.startsWith(path);
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
    border-bottom: 5px solid rgba(0, 47, 167, 1);
  }
}
</style>
