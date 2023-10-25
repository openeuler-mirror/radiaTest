<template>
  <n-card style="height: 100%">
    <n-card title="结果统计" style="margin-bottom: 20px">
      <div style="display: flex">
        <div>
          <span>total:</span> <span style="color: blue">{{ atData.total }}</span>
        </div>
        <div style="margin: 0 20px">
          <span>passed:</span> <span style="color: green">{{ atData.success }}</span>
        </div>
        <div>
          <span>failed:</span> <span style="color: red">{{ atData.failed }}</span>
        </div>
        <div style="margin-left: 20px">
          <span>canceled:</span> <span style="color: orange">{{ atData.canceled }}</span>
        </div>
      </div>
    </n-card>
    <n-data-table
      style="height: calc(100% - 133px)"
      flex-height
      :data="atData.detail_list"
      :bordered="false"
      :columns="atTestsColumns"
      :row-key="(rowData) => rowData.test"
    />
  </n-card>
</template>

<script setup>
import { ref, onMounted, h } from 'vue';
import { useRoute } from 'vue-router';
import { NIcon, NTooltip } from 'naive-ui';
import { Circle24Filled } from '@vicons/fluent';
import axios from '@/axios';
const atTestsColumns = [
  {
    title: '测试项',
    key: 'test',
  },
  {
    title: 'aarch64',
    key: 'aarch64',
    className: 'tests-col',
    render: (row) => {
      if (!row.aarch64 || !row.aarch64.state) {
        return '-';
      }
      if (row.aarch64.result) {
        return h('span', { class: 'tests-res' }, [
          h(
            NTooltip,
            { trigger: 'hover' },
            {
              default: () => `${row.aarch64.state}: ${row.aarch64.result}`,
              trigger: () =>
                h(
                  NIcon,
                  {
                    size: 14,
                    color: renderResColor(row.aarch64.state, row.aarch64.result),
                    style: { cursor: 'pointer' },
                  },
                  { default: () => h(Circle24Filled) }
                ),
            }
          ),
        ]);
      }
      return h(
        NTooltip,
        { trigger: 'hover' },
        {
          default: () => `${row.aarch64.state}: -`,
          trigger: () =>
            h(
              NIcon,
              {
                size: 14,
                color: renderResColor(row.aarch64.state, row.aarch64.result),
                style: { cursor: 'pointer' },
              },
              { default: () => h(Circle24Filled) }
            ),
        }
      );
    },
  },
  {
    title: 'x86_64',
    key: 'x86_64',
    className: 'tests-col',
    render: (row) => {
      if (!row.x86_64 || !row.x86_64.state) {
        return '-';
      }
      if (row.x86_64.result) {
        return h('span', { class: 'tests-res' }, [
          h(
            NTooltip,
            { trigger: 'hover' },
            {
              default: () => `${row.x86_64.state}: ${row.x86_64.result}`,
              trigger: () =>
                h(
                  NIcon,
                  {
                    size: 14,
                    style: { cursor: 'pointer' },
                    color: renderResColor(row.x86_64.state, row.x86_64.result),
                  },
                  { default: () => h(Circle24Filled) }
                ),
            }
          ),
        ]);
      }
      return h(
        NTooltip,
        { trigger: 'hover' },
        {
          default: () => `${row.x86_64.state}: -`,
          trigger: () =>
            h(
              NIcon,
              {
                size: 14,
                color: renderResColor(row.x86_64.state, row.x86_64.result),
                style: { cursor: 'pointer' },
              },
              { default: () => h(Circle24Filled) }
            ),
        }
      );
    },
  },
];
function renderResColor(resStatus, failmodule) {
  if (!resStatus) {
    return 'white';
  }
  switch (true) {
    case resStatus === 'scheduled' && failmodule === 'none':
      return '#0076ff'; //蓝色
    case resStatus === 'running' && failmodule === 'none':
      return '#80b5f2'; //浅蓝色
    case resStatus === 'done' && failmodule === 'passed':
      return '#18A058'; //绿色
    case failmodule === 'skipped' || resStatus === 'cancelled':
      return '#f2e842'; //黄色
    default:
      return '#c20000'; //正红
  }
}

onMounted(() => {
  getAtData();
});
const atData = ref({
  detail_list: [],
  total: 0,
  success: 0,
  failed: 0,
  cancelled: 0,
});
function getAtData() {
  const route = useRoute();
  let params = route.query;
  axios
    .get('/v1/openeuler/at-detail', params)
    .then((res) => {
      atData.value = res.data;
    })
    .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
}
</script>
<style>
.tests-col {
  width: 30%;
}
.tests-res {
  display: flex;
  align-items: center;
}
</style>
