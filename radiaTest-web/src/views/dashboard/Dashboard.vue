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
// import {useRoute} from 'vue-router';

export default defineComponent({
  components: {
    taskManage
  },
  methods: {},
  setup() {
    // const route=useRoute();
    modules.initData();
    // console.log(route.params.workspace);
    return {
      ...modules
    };
  }
});
</script>

<style scoped lang="less"></style>
