<template>
  <n-grid :cols="24" y-gap="20">
    <n-gi :span="2"></n-gi>
    <n-gi :span="22">
      <div style="font-size: 30px; font-weight: 600">
        {{ data.length }} 个任务{{ suffix }}
      </div>
    </n-gi>
    <n-gi :span="2"></n-gi>
    <n-gi :span="14">
      <label style="font-size: 18px; display: inline-block">
        每页
        <n-select
          :options="[
            { label: '5', value: 5 },
            { label: '10', value: 10 },
            { label: '20', value: 20 },
            { label: '50', value: 50 },
          ]"
          @update:value="
            (value) =>
              !value
                ? (pagination.pageSize = 10)
                : (pagination.pageSize = value)
          "
          style="display: inline-block; width: 80px"
          size="small"
          clearable
        />
        个任务
      </label>
    </n-gi>
    <n-gi :span="6">
      <n-input
        v-model:value="searchValue"
        placeholder="搜索任务名......"
        size="large"
        style="width: 95%"
        round
      />
    </n-gi>
    <n-gi :span="2"></n-gi>
    <n-gi :span="2"></n-gi>
    <n-gi :span="22">
      <n-data-table
        ref="tableRef"
        size="medium"
        :columns="columns"
        :data="data"
        :row-key="(row) => row.id"
        :row-props="rowProps"
        style="width: 90%"
        :pagination="pagination"
      />
    </n-gi>
  </n-grid>
</template>

<script>
import { ref, inject, watch, computed, defineComponent } from 'vue';

import { jobsCard } from '@/views/job/modules';

export default defineComponent({
  props: {
    type: {
      default: 'execute',
      type: String,
    },
  },
  setup(props) {
    const suffix = ref('');
    const injectData = inject(props.type);

    const pagination = ref({ pageSize: 10 });
    const columns = ref([]);
    const searchValue = ref('');

    jobsCard.initColumns(columns, props.type);
    jobsCard.initSuffix(suffix, props.type);

    watch(props, jobsCard.initColumns(columns, props.type), { deep: true });

    const data = computed(() => {
      const result = injectData.value.filter(
        (item) =>
          item.name.toLowerCase().search(searchValue.value.toLowerCase()) !== -1
      );
      result.sort((rowA, rowB) => {
        if (rowA.create_time <= rowB.create_time) {
          return 1;
        }
        return -1;
      });
      return result;
    });

    return {
      data,
      suffix,
      columns,
      pagination,
      searchValue,
    };
  },
});
</script>
