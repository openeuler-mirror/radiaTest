<template>
  <n-data-table
    :data="data"
    :columns="columns"
    :row-key="(row) => row.id"
    :row-class-name="
      (row) => {
        if (row.mode === 0 && row.expect_result === row.actual_result) {
          return 'true';
        } else if (row.mode === 1 && row.expect_result !== row.actual_result) {
          return 'true';
        }
        return 'false';
      }
    "
    @update:expanded-row-keys="handleExpand"
  />
</template>

<script>
import { h, ref, defineComponent } from 'vue';
import { NCode } from 'naive-ui';

const basicColumns = [
  {
    title: '测试阶段',
    key: 'stage',
    className: 'cols',
  },
  {
    title: '测试步骤',
    key: 'checkpoint',
    className: 'cols',
  },
  {
    title: '预期结果',
    key: 'expect_result',
    className: 'cols',
  },
  {
    title: '实际结果',
    key: 'actual_result',
    className: 'cols',
  },
  {
    title: '测试预期',
    key: 'mode',
    className: 'cols',
  },
  {
    title: '测试结果',
    key: 'result',
    className: 'cols result',
    render(row) {
      if (row.mode === 0 && row.expect_result === row.actual_result) {
        return h('p', null, '成功');
      } else if (row.mode === 1 && row.expect_result !== row.actual_result) {
        return h('p', null, '成功');
      }
      return h('p', null, '失败');
    },
  },
];

export default defineComponent({
  props: {
    data: {
      default: () => [],
      type: Array,
    },
  },
  setup() {
    const expandedRowKeys = ref([]);
    const columns = [
      {
        type: 'expand',
        renderExpand(row) {
          return h(NCode, {
            language: 'bash',
            code: row.section_log,
            style: {
              overflowX: 'scroll',
            },
          });
        },
      },
      ...basicColumns,
    ];

    return {
      columns,
      handleExpand(rowKeys) {
        expandedRowKeys.value = rowKeys;
      },
    };
  },
});
</script>

<style>
.false .result {
  background-color: rgb(146, 9, 9) !important;
  color: white !important;
  text-align: center !important;
  font-weight: 700 !important;
}
</style>
