<template>
  <n-modal v-model:show="showModal" @afterEnter="modalEnter">
    <n-card
      :title="createTitle('多版本软件包')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true
      }"
      style="width: 1200px"
    >
      <n-tabs animated type="line" v-model:value="roundTab" @update:value="changeRound">
        <n-tab name="oldPackage"> {{ oldPackage.name }} </n-tab>
        <n-tab name="newPackage"> {{ newPackage.name }} </n-tab>
      </n-tabs>
      <n-tabs animated type="line" v-model:value="repoPath" @update:value="changeReoppath">
        <n-tab name="everything"> everything </n-tab>
        <n-tab name="EPOL"> EPOL </n-tab>
      </n-tabs>
      <n-data-table
        remote
        class="tableClass"
        :loading="multiVersionPackageLoading"
        :columns="multiVersionPackageColumns"
        :data="multiVersionPackageData"
        :pagination="multiVersionPackagePagination"
        @update:page="multiVersionPackagePageChange"
        @update:pageSize="multiVersionPackagePageSizeChange"
      />
    </n-card>
  </n-modal>
</template>

<script setup>
import { createTitle } from '@/assets/utils/createTitle';
import { oldPackage, newPackage } from '@/views/versionManagement/product/modules/productDetailDrawer';
import { getMultiVersionPackageAxios } from '@/api/get';

const props = defineProps(['roundCompareeId', 'roundCurId']);
const { roundCompareeId, roundCurId } = toRefs(props);
const showModal = ref(false);
const currentRoundId = ref(null);
const roundTab = ref('oldPackage');
const repoPath = ref('everything');
const multiVersionPackageData = ref([]);
const multiVersionPackageLoading = ref(false);
const multiVersionPackageColumns = ref([
  {
    key: 'rpm_name',
    title: '名称'
  },
  {
    key: 'version',
    title: 'Version版本号',
    align: 'center'
  },
  {
    key: 'release',
    title: 'Release版本号',
    align: 'center'
  },
  {
    key: 'arch',
    title: '架构',
    align: 'center'
  }
]);
const multiVersionPackagePagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1, // 总页数
  itemCount: 1, // 总条数
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100]
});

const getMultiVersionPackage = (roundId, repoPathParam) => {
  multiVersionPackageLoading.value = true;
  getMultiVersionPackageAxios(roundId, {
    repo_path: repoPathParam,
    page_num: multiVersionPackagePagination.value.page,
    page_size: multiVersionPackagePagination.value.pageSize
  }).then((res) => {
    multiVersionPackageLoading.value = false;
    multiVersionPackageData.value = res.data.items;
    multiVersionPackagePagination.value.pageCount = res.data.pages;
    multiVersionPackagePagination.value.itemCount = res.data.total;
  });
};

const multiVersionPackagePageChange = (page) => {
  multiVersionPackagePagination.value.page = page;
  getMultiVersionPackage(currentRoundId.value, repoPath.value);
};

const multiVersionPackagePageSizeChange = (pageSize) => {
  multiVersionPackagePagination.value.page = 1;
  multiVersionPackagePagination.value.pageSize = pageSize;
  getMultiVersionPackage(currentRoundId.value, repoPath.value);
};

const changeRound = (value) => {
  if (value === 'oldPackage') {
    roundTab.value = 'oldPackage';
    currentRoundId.value = roundCompareeId.value;
    multiVersionPackagePagination.value.page = 1;
    getMultiVersionPackage(currentRoundId.value, repoPath.value);
  } else {
    roundTab.value = 'newPackage';
    currentRoundId.value = roundCurId.value;
    multiVersionPackagePagination.value.page = 1;
    getMultiVersionPackage(currentRoundId.value, repoPath.value);
  }
};

const changeReoppath = (value) => {
  repoPath.value = value;
  multiVersionPackagePagination.value.page = 1;
  getMultiVersionPackage(currentRoundId.value, repoPath.value);
};

// 弹框显示回调
const modalEnter = () => {
  roundTab.value = 'oldPackage';
  repoPath.value = 'everything';
  currentRoundId.value = roundCompareeId.value;
  multiVersionPackagePagination.value.page = 1;
  getMultiVersionPackage(currentRoundId.value, repoPath.value);
};

defineExpose({
  showModal
});
</script>

<style scoped lang="less">
.tableClass {
  margin-top: 20px;
}
</style>
