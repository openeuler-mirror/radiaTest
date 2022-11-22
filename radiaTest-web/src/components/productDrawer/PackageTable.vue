<template>
  <n-checkbox-group v-model:value="archesParam">
    <n-space justify="space-between">
      <n-space item-style="display: flex;" v-show="packageTabValueFirst === 'softwarescope'">
        <n-checkbox value="aarch64" label="aarch64" />
        <n-checkbox value="x86_64" label="x86_64" />
        <n-checkbox value="noarch" label="noarch" />
      </n-space>
      <n-space>
        <n-popover>
          <template #trigger>
            <n-button
              style="height: auto"
              circle
              quaternary
              :disabled="buttonDisabled"
              @click="handleCreateClick(qualityboardId, roundPreId, roundCurId, { repo_path: packageTabValueSecond })"
            >
              <template #icon>
                <n-icon>
                  <compare />
                </n-icon>
              </template>
            </n-button>
          </template>
          重新比对
        </n-popover>
        <refresh-button
          :size="18"
          @refresh="
            () => {
              getData(qualityboardId, roundPreId, roundCurId);
            }
          "
        >
          刷新数据（非重新比对）
        </refresh-button>
      </n-space>
    </n-space>
  </n-checkbox-group>
  <n-input-group>
    <n-input v-model:value="thisParams.search" placeholder="搜索软件包..." clearable />
    <n-input-group-label style="width: 15%">
      {{ packageTabValueFirst === 'softwarescope' ? totalNum : frameworktotalNum }} in total
    </n-input-group-label>
  </n-input-group>
  <div v-if="packageTabValueFirst === 'softwarescope'">
    <n-data-table
      remote
      :loading="loading"
      :columns="columns"
      :data="data"
      :bordered="false"
      :pagination="pagination"
      @update:filters="handleFiltersChange"
    />
  </div>
  <div v-else>
    <n-data-table
      remote
      :loading="loading"
      :columns="frameworkColumns"
      :data="frameworkDate"
      :bordered="false"
      :pagination="frameworkPagination"
      @update:filters="frameworkhandleFiltersChange"
    />
  </div>
</template>

<script setup>
import RefreshButton from '@/components/CRUD/RefreshButton';
import { CompareArrowsFilled as Compare } from '@vicons/material';
import {
  oldPackage,
  newPackage,
  packageChangeSummary
} from '@/views/versionManagement/product/modules/productDetailDrawer';
import { getPackageListComparationDetail, getHomonymousIsomerismPkgcompare } from '@/api/get';
import { setPackageListComparationDetail, setHomonymousIsomerismPkgcompare } from '@/api/post';

const props = defineProps([
  'qualityboardId',
  'roundPreId',
  'roundCurId',
  'packageTabValueFirst',
  'packageTabValueSecond'
]);
const { qualityboardId, roundPreId, roundCurId, packageTabValueFirst, packageTabValueSecond } = toRefs(props);
const rpmCompareStatus = ['SAME', 'VER_UP', 'VER_DOWN', 'REL_UP', 'REL_DOWN', 'ADD', 'DEL', 'ERROR'];
const rpmCompareStatusDict = {
  SAME: '一致',
  VER_UP: '版本号升级',
  VER_DOWN: '版本号降级',
  REL_UP: 'release号升级',
  REL_DOWN: 'release号降级',
  ADD: '新增',
  DEL: '移除',
  ERROR: '比对异常'
};
const rpmCompareStatusOptions = rpmCompareStatus.map((item) => {
  return {
    label: rpmCompareStatusDict[item],
    value: item
  };
});
const compareeColumn = reactive({
  key: 'rpm_comparee'
});
const comparerColumn = reactive({
  key: 'rpm_comparer'
});
const compareResultColumn = reactive({
  key: 'compare_result',
  title: '比对结果',
  className: 'compare-result',
  filter: true,
  filterOptionValues: [],
  filterOptions: rpmCompareStatusOptions,
  render: (row) => {
    return h('span', {}, rpmCompareStatusDict[row.compare_result]);
  }
});
const columns = [compareeColumn, comparerColumn, compareResultColumn];
const loading = ref(false);
const data = ref([]);
const totalNum = ref(null);
const archesParam = ref(['aarch64', 'x86_64', 'noarch']);
const thisParams = ref({
  search: null,
  desc: false,
  page_num: 1,
  page_size: 10,
  repo_path: packageTabValueSecond
});

const pagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page) => {
    pagination.page = page;
    thisParams.value.page_num = page;
  },
  onUpdatePageSize: (pageSize) => {
    pagination.pageSize = pageSize;
    pagination.page = 1;
    thisParams.value.page_num = 1;
    thisParams.value.page_size = pageSize;
  }
});
const buttonDisabled = ref(false);
const frameworkStatus = ['SAME', 'DIFFERENT', 'LACK'];
const frameworkStatusDict = {
  SAME: '一致',
  DIFFERENT: '不一致',
  LACK: '缺失'
};
const frameworkStatusOptions = frameworkStatus.map((item) => {
  return {
    label: frameworkStatusDict[item],
    value: item
  };
});
const frameworkCompareResultColumn = reactive({
  key: 'compare_result',
  title: '比对结果',
  className: 'compare-result',
  filter: true,
  filterOptionValues: [],
  filterOptions: frameworkStatusOptions,
  render: (row) => {
    return h('span', {}, frameworkStatusDict[row.compare_result]);
  }
});
const frameworkColumns = reactive([
  { key: 'rpm_arm', title: 'rpm_arm' },
  { key: 'rpm_x86', title: 'rpm_x86' },
  frameworkCompareResultColumn
]);
const frameworkDate = ref([]);
const frameworktotalNum = ref(null);
const frameworkPagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page) => {
    frameworkPagination.page = page;
    thisParams.value.page_num = page;
  },
  onUpdatePageSize: (pageSize) => {
    frameworkPagination.pageSize = pageSize;
    frameworkPagination.page = 1;
    thisParams.value.page_num = 1;
    thisParams.value.page_size = pageSize;
  }
});

function getData(qualityboardIdParam, roundPreIdParam, roundCurIdParam) {
  loading.value = true;
  if (packageTabValueFirst.value === 'softwarescope') {
    getPackageListComparationDetail(qualityboardIdParam, roundPreIdParam, roundCurIdParam, {
      compare_result_list: JSON.stringify(compareResultColumn.filterOptionValues),
      arches: JSON.stringify(archesParam.value),
      ...thisParams.value
    })
      .then((res) => {
        compareeColumn.title = oldPackage.value.name;
        comparerColumn.title = newPackage.value.name;
        data.value = res.data.items;
        totalNum.value = res.data.total;
        pagination.itemCount = res.data.total;
        packageChangeSummary.value.addPackagesNum = res.data.add_pkgs_num;
        packageChangeSummary.value.delPackagesNum = res.data.del_pkgs_num;
        if (roundCurIdParam === roundPreIdParam) {
          data.value.forEach((item) => {
            item.rpm_comparee = null;
            item.compare_result = null;
          });
          packageChangeSummary.value.addPackagesNum = 0;
          packageChangeSummary.value.delPackagesNum = 0;
        }
      })
      .finally(() => {
        loading.value = false;
      });
  } else {
    getHomonymousIsomerismPkgcompare(qualityboardIdParam, roundCurIdParam, {
      compare_result_list: JSON.stringify(frameworkCompareResultColumn.filterOptionValues),
      ...thisParams.value
    })
      .then((res) => {
        frameworkDate.value = res.data.items;
        frameworktotalNum.value = res.data.total;
        frameworkPagination.itemCount = res.data.total;
      })
      .finally(() => {
        loading.value = false;
      });
  }
}

const cleanData = () => {
  loading.value = false;
  data.value = [];
  frameworkDate.value = [];
  thisParams.value = {
    search: null,
    desc: false,
    page_num: 1,
    page_size: 10,
    repo_path: packageTabValueSecond
  };
  archesParam.value = ['aarch64', 'x86_64', 'noarch'];
  totalNum.value = null;
  frameworktotalNum.value = null;
};

// 重新比对
function handleCreateClick(qualityboardIdParam, roundPreIdParam, roundCurIdParam, params) {
  buttonDisabled.value = true;
  window.$message?.loading('开始比对，请稍等');
  if (packageTabValueFirst.value === 'softwarescope') {
    setPackageListComparationDetail(qualityboardIdParam, roundPreIdParam, roundCurIdParam, params)
      .then(() => {
        window.$message?.success('比对成功');
        getData(qualityboardIdParam, roundPreIdParam, roundCurIdParam);
      })
      .catch(() => {
        window.$message?.error('比对失败');
      })
      .finally(() => {
        buttonDisabled.value = false;
      });
  } else {
    setHomonymousIsomerismPkgcompare(qualityboardIdParam, roundCurIdParam, params)
      .then(() => {
        window.$message?.success('比对成功');
        getData(qualityboardIdParam, roundPreIdParam, roundCurIdParam);
      })
      .catch(() => {
        window.$message?.error('比对失败');
      })
      .finally(() => {
        buttonDisabled.value = false;
      });
  }
}

const handleFiltersChange = (filters) => {
  compareResultColumn.filterOptionValues = filters.compare_result || [];
  pagination.page = 1;
  thisParams.value.page_num = 1;
  getData(qualityboardId.value, roundPreId.value, roundCurId.value);
};
const frameworkhandleFiltersChange = (filters) => {
  frameworkCompareResultColumn.filterOptionValues = filters.compare_result || [];
  pagination.page = 1;
  thisParams.value.page_num = 1;
  getData(qualityboardId.value, roundPreId.value, roundCurId.value);
};

watch(
  thisParams,
  () => {
    getData(qualityboardId.value, roundPreId.value, roundCurId.value);
  },
  { deep: true }
);
watch(archesParam, () => {
  getData(qualityboardId.value, roundPreId.value, roundCurId.value);
});
watch(roundCurId, () => {
  totalNum.value = null;
  frameworktotalNum.value = null;
  data.value = [];
  frameworkDate.value = [];
  getData(qualityboardId.value, roundPreId.value, roundCurId.value);
});
watch(packageTabValueFirst, () => {
  getData(qualityboardId.value, roundPreId.value, roundCurId.value);
});
onMounted(() => {
  getData(qualityboardId.value, roundPreId.value, roundCurId.value);
});
onUnmounted(() => {
  cleanData();
});
</script>

<style scoped>
:deep(.compare-result) {
  width: 15%;
}
</style>
