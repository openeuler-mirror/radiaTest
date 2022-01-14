<template>
  <ul class="timeline">
    <slot></slot>
  </ul>
</template>
<script>
export default {
  setup() { },
};
</script>

<style scoped lang="less">
.timeline {
  margin-top: 20px;
  font-size: 14px;
  list-style: none;
  background-color: #fff;
  padding-left: 0;
}
</style>
