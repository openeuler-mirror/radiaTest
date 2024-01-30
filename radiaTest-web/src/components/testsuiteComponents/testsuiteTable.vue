<template>
  <modal-card
    :initY="100"
    :initX="300"
    title="修改测试套"
    ref="putModalRef"
    @validate="() => putFormRef.put()"
  >
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
    remote
    ref="table"
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :pagination="pagination"
    @update:page="testsuitePageChange"
    @update:page-size="testsuitePageSizeChange"
    :row-key="(row) => row.id"
  />
</template>
<script setup>
import { NIcon, NButton, NSpace } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { Delete24Regular } from '@vicons/fluent';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import { renderTooltip } from '@/assets/render/tooltip';
// import { workspace } from '@/assets/config/menu.js';
// import axios from '@/axios';
import { deleteSuiteAxios } from '@/api/delete';
import textDialog from '@/assets/utils/dialog';
import { getSuite } from '@/api/get';
const baseColumns = [
  {
    title: '测试套',
    key: 'name',
    align: 'center',
  },
  {
    title: '节点数',
    key: 'machine_num',
    align: 'center',
  },
  {
    title: '节点类型',
    key: 'machine_type',
    align: 'center',
  },
  {
    title: '备注',
    key: 'remark',
    align: 'center',
  },
  {
    title: '责任人',
    key: 'owner',
    align: 'center',
  },
];
function createBtn(type, icon, text, clickFn, row) {
  return renderTooltip(
    h(
      NButton,
      {
        size: 'medium',
        type,
        circle: true,
        onClick: () => clickFn(row),
      },
      h(NIcon, { size: '20' }, h(icon))
    ),
    text
  );
}
const loading = ref(false);
const putFormRef = ref(null);
const pagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50],
});
const data = ref([]);
const getData = () => {
  let param = {
    page_num: pagination.value.page,
    page_size: pagination.value.pageSize,
  };
  loading.value = true;
  getSuite(param)
    .then((res) => {
      data.value = res.data.items;
      pagination.value.pageCount = res.data.pages;
      pagination.value.page = res.data.current_page;
      pagination.value.pageSize = res.data.page_size;
      loading.value = false;
    })
    .catch(() => {
      loading.value = false;
    });
};
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
          align: 'cemter',
        },
        [
          createBtn('warning', Construct, '修改', editSuite, row),
          createBtn('error', Delete24Regular, '删除', deleteSuite, row),
        ]
      );
    },
  },
];

const testsuitePageChange = (page) => {
  pagination.value.page = page;
  getData();
};

const testsuitePageSizeChange = (pageSize) => {
  pagination.value.pageSize = pageSize;
  pagination.value.page = 1;
  getData();
};

onMounted(() => {
  getData();
});

defineExpose({ data, getData, pagination });
</script>
