<template>
  <div>
    <vue-kityminder
      ref="kityminderRef"
      theme="fresh-blue"
      template="right"
      :toolbar-status="toolbar"
      :value="kityminderValue"
    ></vue-kityminder>
  </div>
</template>

<script setup>
const kityminderRef = ref(null);
const toolbar = ref({
  appendSiblingNode: true, // 插入同级
  appendChildNode: true, // 插入下级
  arrangeUp: true, // 上移
  arrangeDown: true, // 下移
  removeNode: true, // 删除
  text: true, // 文本框
  template: false, // 模板
  theme: false, // 主题
  hand: true, // 模式
  resetLayout: true, // 整理布局
  zoomOut: true, // 缩小
  zoomIn: true // 放大
});
const kityminderValue = ref(null);
</script>

<style scoped lang="less"></style>
