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
import modules from './index';

export default defineComponent({
  components: {
    taskManage
  },
  methods: {},
  setup() {
    modules.iframeLogin();
    return {
      ...modules
    };
  },
  beforeUnmount() {
    window.removeEventListener('message', modules.getIframeMessage(), false);
  }
});
</script>

<style scoped lang="less"></style>
