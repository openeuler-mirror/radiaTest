<template>
  <div v-if="currentFeature?.type === 'featureSet'" class="content-wrap">
    <n-data-table
      remote
      :loading="featureSetTableLoading"
      :data="featureSetTableData"
      :columns="featureSetTableColumns"
      :pagination="featureSetTablePagination"
      @update:page="featureSetTablePageChange"
      @update:pageSize="featureSetTablePageSizeChange"
    />
  </div>
  <div v-else class="empty-wrap">
    <n-empty size="large"> </n-empty>
  </div>
</template>

<script setup>
import { getAllFeature } from '@/api/get';

const props = defineProps(['currentFeature']);
const { currentFeature } = toRefs(props);

const featureSetTableLoading = ref(false);
const featureSetTableData = ref([]);
const featureSetTableColumns = ref([
  {
    key: 'no',
    title: '编号',
    align: 'center'
  },
  {
    key: 'feature',
    title: '名称'
  },
  {
    key: 'release_to',
    title: 'release to',
    align: 'center'
  },
  {
    key: 'pkgs',
    title: '包',
    align: 'center'
  },
  {
    key: 'owner',
    title: '拥有者',
    align: 'center'
  },
  {
    key: 'sig',
    title: 'sig组',
    align: 'center'
  },
  {
    key: 'url',
    title: 'URL',
    align: 'center'
  }
]);
const featureSetTablePagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1, // 总页数
  itemCount: 1, // 总条数
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100]
});

const getFeatureSet = (
  pageNum = featureSetTablePagination.value.page,
  pageSize = featureSetTablePagination.value.pageSize
) => {
  featureSetTableLoading.value = true;
  featureSetTableData.value = [];
  getAllFeature({
    page_num: pageNum,
    page_size: pageSize
  }).then((res) => {
    featureSetTableLoading.value = false;
    res.data?.items?.forEach((v) => {
      featureSetTableData.value.push({
        no: v.no,
        feature: v.feature,
        release_to: v.release_to,
        pkgs: v.pkgs?.join(','),
        owner: v.owner?.join(','),
        sig: v.sig?.join(','),
        url: v.url
      });
    });
    featureSetTablePagination.value.page = res.data.current_page;
    featureSetTablePagination.value.pageCount = res.data.pages;
    featureSetTablePagination.value.itemCount = res.data.total;
  });
};

const featureSetTablePageChange = (page) => {
  featureSetTablePagination.value.page = page;
  getFeatureSet();
};

const featureSetTablePageSizeChange = (pageSize) => {
  featureSetTablePagination.value.page = 1;
  featureSetTablePagination.value.pageSize = pageSize;
  getFeatureSet();
};

onMounted(() => {
  getFeatureSet();
});

defineExpose({
  getFeatureSet
});
</script>

<style scoped lang="less">
.content-wrap {
  height: 100%;
}
.empty-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
