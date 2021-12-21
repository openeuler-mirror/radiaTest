<template>
  <n-input-group>
    <n-input
      v-model:value="filterValue.suite"
      :style="{ width: '10%' }"
      round
      placeholder="测试套"
    />
    <n-input
      v-model:value="filterValue.name"
      size="large"
      :style="{ width: '25%' }"
      placeholder="用例名"
      clearable
    />
    <n-select
      v-model:value="filterValue.test_level"
      size="large"
      :style="{ width: '8%' }"
      :options="[
        {
          label: '系统测试',
          value: '系统测试',
        },
        {
          label: '集成测试',
          value: '集成测试',
        },
        {
          label: '单元测试',
          value: '单元测试',
        },
      ]"
      placeholder="测试等级"
    />
    <n-select
      v-model:value="filterValue.test_type"
      size="large"
      :style="{ width: '8%' }"
      :options="[
        {
          label: '功能测试',
          value: '功能测试',
        },
        {
          label: '安全测试',
          value: '安全测试',
        },
        {
          label: '性能测试',
          value: '性能测试',
        },
        {
          label: '压力测试',
          value: '压力测试',
        },
        {
          label: '可靠性测试',
          value: '可靠性测试',
        },
      ]"
      placeholder="测试类型"
    />
    <n-input
      v-model:value="filterValue.machine_num"
      :style="{ width: '5%' }"
      round
      placeholder="节点数"
    />
    <n-select
      v-model:value="filterValue.machine_type"
      size="large"
      :style="{ width: '5%' }"
      placeholder="节点类型"
      :options="[
        { label: '虚拟机', value: 'kvm' },
        { label: '物理机', value: 'physical' },
      ]"
      clearable
    />
    <n-select
      v-model:value="filterValue.automatic"
      :style="{ width: '6%' }"
      size="large"
      :options="[
        { label: '是', value: true },
        { label: '否', value: false },
      ]"
      round
      placeholder="自动化"
    />
    <n-input
      v-model:value="filterValue.remark"
      :style="{ width: '12%' }"
      round
      placeholder="备注"
    />
    <n-input
      v-model:value="filterValue.owner"
      :style="{ width: '12%' }"
      round
      placeholder="责任人"
    />
    <clear-input @clearAll="clearAll" />
  </n-input-group>
</template>

<script>
import { watch, defineComponent } from 'vue';
import { useStore } from 'vuex';

import ClearInput from '@/components/CRUD/ClearInput.vue';

import testcaseFilter from '@/views/caseManage/testcase/modules/testcaseFilter.js';

export default defineComponent({
  components: {
    ClearInput,
  },
  setup() {
    const store = useStore();

    watch(
      testcaseFilter.filterValue,
      () => {
        store.commit('filterCase/setAll', testcaseFilter.filterValue.value);
      },
      { deep: true }
    );

    return {
      ...testcaseFilter,
    };
  },
});
</script>

<style scoped></style>
