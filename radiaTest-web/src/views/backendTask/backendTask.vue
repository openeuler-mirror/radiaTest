<template>
  <div class="container">
    <div class="task-header">
      <n-h2>后台任务</n-h2>
      <n-inpu
        v-model:value="searchInfo"
        round
        placeholder="请输入"
        @change="searchTask"
      />
    </div>
    <div>
      <n-data-table
        :bordered="false"
        :columns="taskColumns"
        :data="taskData"
        :loading="loading"
        :pagination="pagination"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
        remote
      />
    </div>
  </div>
</template>
<script>
import { modules } from './modules';
export default {
  setup() {
    modules.connectSocket();
    modules.getTask();
    return {
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.container {
  padding: 10px;
  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
