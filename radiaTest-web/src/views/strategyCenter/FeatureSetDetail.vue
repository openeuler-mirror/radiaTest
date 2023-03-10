<template>
  <div v-if="currentFeature" class="content-wrap">
    <n-descriptions label-placement="left" bordered title="特性详情" :column="2" size="large">
      <n-descriptions-item label="特性名"> {{ currentFeature.info.feature }} </n-descriptions-item>
      <n-descriptions-item label="特性编号"> {{ currentFeature.info.no }} </n-descriptions-item>
      <n-descriptions-item label="releast to"> {{ currentFeature.info.release_to }} </n-descriptions-item>
      <n-descriptions-item label="特性包"> {{ currentFeature.info.pkgs }} </n-descriptions-item>
      <n-descriptions-item label="拥有者"> {{ currentFeature.info.owner?.join() }} </n-descriptions-item>
      <n-descriptions-item label="sig组"> {{ currentFeature.info.sig?.join() }} </n-descriptions-item>
      <n-descriptions-item label="URL"> {{ currentFeature.info.url }} </n-descriptions-item>
    </n-descriptions>
  </div>
  <div v-else class="empty-wrap">
    <n-empty size="large"> </n-empty>
  </div>
</template>

<script setup>
const props = defineProps(['currentFeature']);
const { currentFeature } = toRefs(props);
</script>

<style scoped lang="less">
.content-wrap {
  height: 100%;
}
.empty-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
