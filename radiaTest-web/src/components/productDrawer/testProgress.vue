<template>
  <div id="container">
    <div style="height: 100%; width: 76%; overflow-y: scroll">
      <collapseList :list="treeList" v-if="treeList.length > 0" />
      <n-empty style="height: 60%; justify-content: center" description="暂无测试进展" v-else />
    </div>
    <div style="height: 100%; width: 24%; padding-left: 10px">
      <n-anchor offset-target="#container" show-rail>
        <n-anchor-link v-for="item in treeList" :title="item.title" :href="`#${item.id}`" :key="item.id" />
      </n-anchor>
    </div>
  </div>
</template>
<script>
import collapseList from '@/components/productDrawer/collapseList.vue';
export default {
  components: {
    collapseList
  },
  props: {
    treeList: {
      type: Array,
      default: () => []
    }
  }
};
</script>
<style scoped lang="less">
#container {
  display: flex;
  height: 400px;
}
</style>
