<template>
  <div id="container">
    <div style="height: 100%; width: 100%; overflow-y: scroll">
      <collapseProList :treeList="treeList" v-if="treeList.length > 0" />
      <n-empty v-else style="height: 60%; justify-content: center" description="暂无测试进展" />
    </div>
  </div>
</template>

<script setup>
import collapseProList from '@/components/productDrawer/drawerCollapseList.vue';
import { getMilestoneProgress } from '@/api/get.js';

const props = defineProps(['defaultMilestoneId']);
const { defaultMilestoneId } = toRefs(props);
const treeList = ref([]);
provide('defaultMilestoneId', defaultMilestoneId);

const exchangeProgress = (progress) => {
  let obj = {};
  obj.total = progress.all_cnt;
  obj.failure = progress.failed;
  obj.block = progress.pending;
  obj.success = progress.success;
  obj.running = progress.running;
  return obj;
};

const getTreeList = () => {
  getMilestoneProgress(defaultMilestoneId.value)
    .then((res) => {
      treeList.value = [];
      treeList.value.push({
        title: res.data.title,
        progress: exchangeProgress(res.data.test_progress),
        id: res.data.id,
        type: res.data.type,
        is_root: true,
      });
    })
    .catch(() => {
      treeList.value = [];
    });
};

watch(props, () => {
  getTreeList();
});

onMounted(() => {
  if (defaultMilestoneId.value) {
    getTreeList();
  }
});
</script>

<style scoped lang="less">
#container {
  display: flex;
  height: 400px;
  padding: 20px;
}
</style>
