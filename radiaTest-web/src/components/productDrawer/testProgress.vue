<template>
  <div id="container">
    <collapseList :list="treeList" />
    <n-anchor show-rail class="anchor">
      <n-anchor-link v-for="item in treeList" :title="item.title" :href="`#${item.id}`" :key="item.id" />
    </n-anchor>
  </div>
</template>
<script>
import collapseList from '@/components/productDrawer/collapseList.vue';
export default {
  components: {
    collapseList,
  },
  props: {
    treeList: Array,
  },
};
</script>
<style scoped lang="less">
#container{
  display: flex;
  height:100%;
  .anchor{
    flex-shrink: 0;
    width: 23%;
  }
}
</style>
