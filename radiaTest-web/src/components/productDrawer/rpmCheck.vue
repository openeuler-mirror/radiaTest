<template>
  <div v-show="!showDetail">
    <n-data-table
      remote
      :loading="rpmcheckLoading"
      :columns="rpmcheckColumns"
      :data="rpmcheckTableData"
      :pagination="rpmcheckPagination"
      @update:page="rpmcheckPageChange"
      @update:page-size="rpmcheckPageSizeChange"
    />
  </div>
  <div v-show="showDetail">
    <div class="backIconWrap">
      <n-icon size="30" class="backIcon" @click="clickBackIcon">
        <ArrowBackUp />
      </n-icon>
    </div>
    <n-data-table
      remote
      :loading="rpmcheckDetailLoading"
      :columns="rpmcheckDetailColumns"
      :data="rpmcheckDetailTableData"
      :pagination="rpmcheckDetailPagination"
      @update:page="rpmcheckDetailPageChange"
      @update:page-size="rpmcheckDetailPageSizeChange"
    />
  </div>
</template>

<script setup>
import { useTable } from '@/hooks/useTable';
import { ArrowBackUp } from '@vicons/tabler';

const props = defineProps(['qualityBoardId']);
let { qualityBoardId } = toRefs(props);
const showDetail = ref(false);
const rpmcheckLoading = ref(false);
const rpmcheckColumns = [
  {
    title: '名称',
    render: (row) =>
      h(
        'div',
        {
          class: 'rpmcheckName',
          onClick: () => {
            useTable(
              `v1/rpmcheck/${row.id}`,
              rpmcheckDetailParams.value,
              rpmcheckDetailTableData,
              rpmcheckDetailPagination,
              rpmcheckDetailLoading
            );
            showDetail.value = true;
          }
        },
        row.name
      )
  },
  { title: '软件包数量', key: 'all_cnt', align: 'center' },
  { title: '构建时间', key: 'build_time', align: 'center' },
  { title: '成功率', key: 'success_rate', align: 'center' },
  { title: '失败率', key: 'failed_rate', align: 'center' },
  { title: '中断率', key: 'broken_rate', align: 'center' },
  { title: '未解决率', key: 'unresolvable_rate', align: 'center' }
];
const rpmcheckTableData = ref([]);
const rpmcheckPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const rpmcheckParams = ref({
  page_num: toRef(rpmcheckPagination.value, 'page'),
  page_size: toRef(rpmcheckPagination.value, 'pageSize')
});
const rpmcheckPageChange = (page) => {
  rpmcheckPagination.value.page = page;
};
const rpmcheckPageSizeChange = (pageSize) => {
  rpmcheckPagination.value.pageSize = pageSize;
  rpmcheckPagination.value.page = 1;
};

const rpmcheckDetailLoading = ref(false);
const rpmcheckDetailColumns = [
  {
    title: '软件包名',
    key: 'package'
  },
  {
    title: '架构',
    key: 'arch',
    align: 'center'
  },
  {
    title: 'build结果',
    key: 'status',
    align: 'center'
  },
  {
    title: '失败类型',
    key: 'failed_type',
    align: 'center'
  },
  {
    title: '失败详情',
    key: 'failed_detail'
  }
];
const rpmcheckDetailTableData = ref([]);
const rpmcheckDetailPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const rpmcheckDetailParams = ref({
  page_num: toRef(rpmcheckDetailPagination.value, 'page'),
  page_size: toRef(rpmcheckDetailPagination.value, 'pageSize')
});
const rpmcheckDetailPageChange = (page) => {
  rpmcheckDetailPagination.value.page = page;
};
const rpmcheckDetailPageSizeChange = (pageSize) => {
  rpmcheckDetailPagination.value.pageSize = pageSize;
  rpmcheckDetailPagination.value.page = 1;
};

const clickBackIcon = () => {
  showDetail.value = false;
};

useTable(
  `/v1/qualityboard/${qualityBoardId.value}/rpmcheck`,
  rpmcheckParams.value,
  rpmcheckTableData,
  rpmcheckPagination,
  rpmcheckLoading
);
</script>

<style lang="less">
.rpmcheckName {
  color: #2080f0 !important;
  cursor: pointer;
}

.backIconWrap {
  display: flex;
  justify-content: right;

  .backIcon {
    cursor: pointer;
    margin: 0 10px;
  }
}
</style>
