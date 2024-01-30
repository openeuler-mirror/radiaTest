<template>
  <div class="home">
    <transition name="mode-fade" mode="out-in" style="height: 100%">
      <task-manage />
    </transition>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import taskManage from '@/views/taskManage/TaskManage';

export default defineComponent({
  components: {
    taskManage,
  },
  methods: {},
  setup() {},
});
</script>

<style scoped lang="less"></style>
