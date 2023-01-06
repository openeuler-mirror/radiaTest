<template>
  <div v-show="!showDetail">
    <n-data-table
      :loading="rpmcheckLoading"
      :columns="rpmcheckColumns"
      :data="rpmcheckTableData"
      :pagination="rpmcheckPagination"
      :row-key="rpmcheckRowKey"
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
import { getRpmcheck } from '@/api/get';

const props = defineProps(['qualityBoardId']);
let { qualityBoardId } = toRefs(props);
const showDetail = ref(false);
const rpmcheckLoading = ref(false);
let stop; // 清除副作用
const rpmcheckColumns = [
  {
    title: '名称',
    render: (row) =>
      h(
        'div',
        {
          class: 'rpmcheckName',
          onClick: () => {
            rpmcheckDetailParams.value.name = row.name;
            rpmcheckDetailPagination.value.page = 1;
            stop = useTable(
              'v1/rpmcheck',
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
  { title: '软件包总数', key: 'all_cnt', align: 'center' },
  { title: '构建时间', key: 'build_time', align: 'center' },
  { title: '状态', key: 'status', align: 'center' },
  { title: '数量', key: 'cnt', align: 'center' },
  { title: '占比', key: 'rate', align: 'center' }
];
const rpmcheckTableData = ref([]);
const rpmcheckPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const rpmcheckPageChange = (page) => {
  rpmcheckPagination.value.page = page;
};
const rpmcheckPageSizeChange = (pageSize) => {
  rpmcheckPagination.value.pageSize = pageSize;
  rpmcheckPagination.value.page = 1;
};
const rpmcheckRowKey = (row) => row.index;
const getRpmcheckData = () => {
  getRpmcheck(qualityBoardId.value).then((res) => {
    rpmcheckTableData.value = [];
    res.data.forEach((v, i) => {
      rpmcheckTableData.value.push({
        index: i,
        name: v.name,
        all_cnt: v.all_cnt,
        build_time: v.build_time,
        children: v.data
      });
    });
  });
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
  page_size: toRef(rpmcheckDetailPagination.value, 'pageSize'),
  name: null
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
  stop();
};

onMounted(() => {
  getRpmcheckData();
});
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
