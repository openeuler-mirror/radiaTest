<template>
  <n-collapse>
    <n-collapse-item v-for="(item, index) in list" :key="index" :title="item.title" :id="item.id">
      <collapseList v-if="item.children" :list="item.children" />
      <template v-else>
        <div class="case-item" v-for="(it, ix) in item.list" :key="ix">
          <p>{{ it.name }}</p>
          <n-icon :color="it.success ? 'green' : 'red'">
            <CloseCircle v-if="it.success" />
            <ChevronDownCircle v-else />
          </n-icon>
        </div>
      </template>
      <template #header-extra v-if="item.progress !== undefined">
        <!-- <n-progress
          style="width:80%"
          type="line"
          :percentage="item.progress"
          indicator-placement="inside"
          processing
        /> -->
        <custom-progress :progress="item.progress"> </custom-progress>
      </template>
    </n-collapse-item>
  </n-collapse>
</template>
<script>
import { ChevronDownCircle, CloseCircle } from '@vicons/ionicons5';
import customProgress from '@/components/customProgress/customProgress.vue';
export default {
  name: 'collapseList',
  components: {
    customProgress,
    ChevronDownCircle,
    CloseCircle
  },
  props: {
    list: Array
  }
};
</script>
<style lang="less" scoped>
.case-item {
  display: flex;
  justify-content: space-evenly;
  align-items: center;
}
</style>

<style scoped>
.n-collapse {
  width: 100%;
  margin-right: 30px;
}
</style>
