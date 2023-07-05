<template>
  <modal-card :initY="100" :initX="300" title="修改测试套" ref="putModalRef" @validate="() => putFormRef.put()">
    <template #form>
      <testsuite-create
        ref="putFormRef"
        :data="suiteInfo"
        @getDataEmit="getData"
        @close="
          () => {
            putModalRef.close();
          }
        "
      />
    </template>
  </modal-card>
  <n-data-table
    ref="table"
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :pagination="pagination"
    :row-key="(row) => row.id"
  />
</template>
<script setup>
import { NIcon, NButton, NSpace } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { Delete24Regular } from '@vicons/fluent';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import { renderTooltip } from '@/assets/render/tooltip';
import { workspace } from '@/assets/config/menu.js';
import axios from '@/axios';
import { deleteSuiteAxios } from '@/api/delete';
import textDialog from '@/assets/utils/dialog';

const baseColumns = [
  {
    title: '测试套',
    key: 'name',
    align: 'center'
  },
  {
    title: '节点数',
    key: 'machine_num',
    align: 'center'
  },
  {
    title: '节点类型',
    key: 'machine_type',
    align: 'center'
  },
  {
    title: '备注',
    key: 'remark',
    align: 'center'
  },
  {
    title: '责任人',
    key: 'owner',
    align: 'center'
  }
];
function createBtn(type, icon, text, clickFn, row) {
  return renderTooltip(
    h(
      NButton,
      {
        size: 'medium',
        type,
        circle: true,
        onClick: () => clickFn(row)
      },
      h(NIcon, { size: '20' }, h(icon))
    ),
    text
  );
}

function getData() {
  loading.value = true;
  axios.get(`/v1/ws/${workspace.value}/suite`).then((res) => {
    data.value = res.data;
    loading.value = false;
  });
}

function setPagination() {
  pagination.value = {
    page: 1,
    showSizePicker: true,
    pageSize: 10,
    pageSizes: [5, 10, 20, 50],
    onChange: (page) => {
      pagination.value.page = page;
    },
    onPageSizeChange: (pageSize) => {
      pagination.value.pageSize = pageSize;
      pagination.value.page = 1;
    }
  };
}

const suiteInfo = ref();
const putModalRef = ref(null);

function editSuite(row) {
  suiteInfo.value = row;
  putModalRef.value.show();
}

function deleteSuite(row) {
  textDialog('warning', '警告', '你确定要删除此测试套吗?', async () => {
    await deleteSuiteAxios(row.id);
    pagination.value.page = 1;
    getData();
  });
}

const data = ref([]);
const columns = [
  ...baseColumns,
  {
    title: '操作',
    key: 'action',
    align: 'center',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'cemter'
        },
        [
          createBtn('warning', Construct, '修改', editSuite, row),
          createBtn('error', Delete24Regular, '删除', deleteSuite, row)
        ]
      );
    }
  }
];

const pagination = ref();
const loading = ref(false);
const putFormRef = ref(null);

onMounted(() => {
  getData();
  setPagination();
});

defineExpose({ data, getData, pagination });
</script>
