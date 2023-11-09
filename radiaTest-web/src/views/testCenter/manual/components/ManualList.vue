<template>
  <n-grid :cols="24" y-gap="20">
    <n-gi :span="24">
      <div style="font-size: 30px; font-weight: 600">{{ totalTask }} 个任务{{ suffix }}</div>
    </n-gi>
    <n-gi :span="16">
      <label style="font-size: 18px; display: inline-block">
        每页
        <n-select
          :default-value="5"
          :options="[
            { label: '5', value: 5 },
            { label: '10', value: 10 },
            { label: '20', value: 20 },
            { label: '50', value: 50 },
          ]"
          @update:value="handleUpdatePage"
          style="display: inline-block; width: 80px"
          size="small"
        />
        个任务
      </label>
    </n-gi>
    <n-gi :span="8">
      <n-input
        v-model:value="searchValue"
        placeholder="搜索任务名......"
        size="large"
        style="width: 100%"
        round
        @keyup="getData"
      />
    </n-gi>
    <n-gi :span="24" ref="tableParent">
      <n-data-table
        ref="tableRef"
        size="medium"
        :columns="columns"
        :data="data"
        :row-key="(row) => row.id"
        :pagination="pagination"
        @update:page="pageChange"
        remote
        :indent="20"
        :key="type"
      />
    </n-gi>
  </n-grid>
</template>

<script setup>
import { ref, watch, onMounted, h } from 'vue';
import { getManualJobGroup } from '@/api/get';
import { deleteManualTask } from '@/api/delete';
import { copyManualTask } from '@/api/post';
import { unkonwnErrorMsg } from '@/assets/utils/description';

import { NIcon, NButton, NProgress, NSpace } from 'naive-ui';
import textDialog from '@/assets/utils/dialog';
import { renderTooltip } from '@/assets/render/tooltip';
import {
  Delete24Regular as Delete,
  Play12Filled as Play,
  Copy20Regular as Copys,
} from '@vicons/fluent';
import manual from '@/views/testCenter/manual/modules/manual';

const executeColumns = [
  {
    key: 'index',
    title: '编号',
    align: 'center',
    render: (row, index) => index + 1,
  },
  {
    key: 'name',
    title: '名称',
    align: 'center',
  },
  {
    key: 'milestone',
    title: '里程碑',
    align: 'center',
  },

  {
    key: 'progress',
    title: '执行进度',
    align: 'center',
    render: (row) => {
      return h(NProgress, {
        type: 'line',
        percentage: Math.round(((row.success + row.failed + row.block) / row.total) * 100),
        indicatorPlacement: 'inside',
        processing: true,
      });
    },
  },
  {
    key: 'create_time',
    title: '开始时间',
    align: 'center',
  },
  {
    key: 'total',
    title: '用例数量',
    align: 'center',
  },

  {
    title: '操作',
    align: 'center',
    fixed: 'right',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center',
        },
        [
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'primary',
                circle: true,
                onClick: () => {
                  manual.excuteDrawerRef.value.showDrawerCb(row);
                },
              },
              h(NIcon, { size: '20' }, h(Play))
            ),
            '执行'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: (e) => {
                  e.stopPropagation();
                  textDialog('warning', '警告', '确认删除手工测试任务？', () => {
                    deleteManualTask(row.id)
                      .then(() => {
                        pagination.value.page = 1;
                        getData();
                      })
                      .catch(() => {});
                  });
                },
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'info',
                circle: true,
                onClick: (e) => {
                  e.stopPropagation();
                  textDialog('warning', '警告', '确认复制手工测试任务？', () => {
                    copyManualTask({ id: row.id })
                      .then(() => {
                        pagination.value.page = 1;
                        getData();
                      })
                      .catch(() => {});
                  });
                },
              },
              h(NIcon, { size: '20' }, h(Copys))
            ),
            '复制'
          ),
        ]
      );
    },
  },
];

const finishColumns = [
  {
    key: 'index',
    title: '编号',
    align: 'center',
    render: (row, index) => index + 1,
  },
  {
    key: 'name',
    title: '名称',
    align: 'center',
  },
  {
    key: 'milestone',
    title: '里程碑',
    align: 'center',
  },

  {
    key: 'update_time',
    title: '结束时间',
    align: 'center',
  },
  {
    key: 'log',
    title: '执行日志',
    align: 'center',
    render: (row) => {
      return h(
        NButton,
        {
          onClick: () => {
            manual.excuteDrawerRef.value.showDrawerCb(row);
          },
        },
        '查看'
      );
    },
  },
  {
    key: 'total',
    title: '用例数量',
    align: 'center',
  },
  {
    key: 'total',
    title: '完成率',
    align: 'center',
    render: (row) => `${Math.round(((row.success + row.failed + row.block) / row.total) * 100)}%`,
  },
  {
    key: 'total',
    title: '通过率',
    align: 'center',
    render: (row) => `${Math.round((row.success / row.total) * 100)}%`,
  },
  {
    title: '操作',
    align: 'center',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center',
        },
        [
          h(
            NButton,
            {
              onClick: () => {
                manual.resultCountDrawerRef.value.showResultDrawerCb(row);
              },
            },
            '结果统计'
          ),
        ]
      );
    },
  },
];
const props = defineProps({
  type: {
    default: 'execute',
    type: String,
  },
  total: Number,
});
onMounted(() => {
  getData();
});
const suffix = ref('');

const pagination = ref({
  page: 1,
  pageCount: 1,
  pageSize: 5,
});
const columns = ref([]);
const searchValue = ref('');
const formatTime = (time) => {
  return time
    ? new Date(time).toLocaleString('zh-CN', { hourCycle: 'h23' }).replace(/\//g, '-')
    : 0;
};
const totalTask = ref(0);
const getData = () => {
  const params = {
    page_size: pagination.value.pageSize,
    page_num: pagination.value.page,
    name: searchValue.value,
  };
  if (props.type === 'execute') {
    params.status = 0;
  } else if (props.type === 'finish') {
    params.status = 1;
  }
  getManualJobGroup(params)
    .then((res) => {
      res.data?.items?.forEach((item) => {
        item.create_time = formatTime(item.create_time);
        item.update_time = formatTime(item.update_time);
      });
      if (props.type === 'finish') {
        data.value = res.data?.items || [];
      } else {
        data.value = res.data?.items || [];
      }
      totalTask.value = res.data.total;
      pagination.value.pageCount = res.data.pages;
    })
    .catch((err) => window.$message?.error(err.data.error_msg || unkonwnErrorMsg));
};
const pageChange = (page) => {
  pagination.value.page = page;
  getData();
};
const handleUpdatePage = (value) => {
  pagination.value.pageSize = value;
  getData();
};

const data = ref([]);

const tableRef = ref(null);
const initColumns = () => {
  if (props.type === 'execute') {
    columns.value = executeColumns;
  } else {
    columns.value = finishColumns;
  }
};
const initSuffix = () => {
  if (props.type === 'execute') {
    suffix.value = '正在执行';
  } else {
    suffix.value = '已完成';
  }
};

initColumns();
initSuffix();
watch(props, initColumns(columns, props.type), { deep: true });
defineExpose({
  getData,
});
</script>
