<template>
  <n-checkbox-group v-model:value="archesParam" :min="1">
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
              @click="
                handleCreateClick(qualityboardId, roundCompareeId, roundCurId, { repo_path: packageTabValueSecond })
              "
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
        <n-popover>
          <template #trigger>
            <n-button style="height: auto" circle quaternary @click="exportPackageComparationFn">
              <template #icon>
                <n-icon>
                  <FileExport />
                </n-icon>
              </template>
            </n-button>
          </template>
          导出比对结果
        </n-popover>
        <n-popover>
          <template #trigger>
            <n-button
              style="height: auto"
              circle
              quaternary
              @click="showMultiVersionPackage"
              :disabled="!hasMultiVersionPackage"
            >
              <template #icon>
                <n-icon>
                  <Package />
                </n-icon>
              </template>
            </n-button>
          </template>
          多版本软件包
        </n-popover>
        <refresh-button
          :size="18"
          @refresh="
            () => {
              softwarescopePagination.page = 1;
              frameworkPagination.page = 1;
              getData(qualityboardId, roundCompareeId, roundCurId);
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
      {{ packageTabValueFirst === 'softwarescope' ? softwarescopeTotalNum : frameworktotalNum }} in total
    </n-input-group-label>
  </n-input-group>
  <div v-if="packageTabValueFirst === 'softwarescope'">
    <n-data-table
      remote
      :loading="loading"
      :columns="softwarescopeColumns"
      :data="softwarescopeTableData"
      :bordered="false"
      :pagination="softwarescopePagination"
      @update:filters="softwarescopeFiltersChange"
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
      @update:filters="frameworkFiltersChange"
    />
  </div>
  <MultiVersionPackage ref="multiVersionPackageRef" :roundCurId="roundCurId"></MultiVersionPackage>
</template>

<script setup>
import RefreshButton from '@/components/CRUD/RefreshButton';
import { CompareArrowsFilled as Compare } from '@vicons/material';
import { FileExport, Package } from '@vicons/tabler';
import {
  oldPackage,
  newPackage,
  packageChangeSummary
} from '@/views/versionManagement/product/modules/productDetailDrawer';
import { getPackageListComparationDetail, getHomonymousIsomerismPkgcompare } from '@/api/get';
import { setPackageListComparationDetail, setHomonymousIsomerismPkgcompare } from '@/api/post';
import MultiVersionPackage from './MultiVersionPackage.vue';
import axios from '@/axios';

const props = defineProps([
  'qualityboardId',
  'roundCompareeId',
  'roundCurId',
  'packageTabValueFirst',
  'packageTabValueSecond',
  'hasMultiVersionPackage'
]);
const {
  qualityboardId,
  roundCompareeId,
  roundCurId,
  packageTabValueFirst,
  packageTabValueSecond,
  hasMultiVersionPackage
} = toRefs(props);

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

// 软件范围比对结果筛选项
const rpmCompareStatusOptions = rpmCompareStatus.map((item) => {
  return {
    label: rpmCompareStatusDict[item],
    value: item
  };
});
// 被比较列（第一列）
const compareeColumn = reactive({
  key: 'rpm_comparee',
  title: oldPackage.value.name
});
// 比较列（第二列）
const comparerColumn = reactive({
  key: 'rpm_comparer',
  title: newPackage.value.name
});
// 比对结果列
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
// 软件范围表格列
const softwarescopeColumns = computed(() => {
  return [compareeColumn, comparerColumn, compareResultColumn];
});

const loading = ref(false); // 表格加载状态
const softwarescopeTableData = ref([]); // 软件范围表格数据
const softwarescopeTotalNum = ref(null); // 软件范围表格总数
const archesParam = ref(['aarch64', 'x86_64', 'noarch']); // arches参数
// 比对参数
const thisParams = ref({
  search: null,
  desc: false,
  repo_path: packageTabValueSecond
});

const softwarescopePagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page) => {
    softwarescopePagination.page = page;
    getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
  },
  onUpdatePageSize: (pageSize) => {
    softwarescopePagination.pageSize = pageSize;
    softwarescopePagination.page = 1;
    getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
  }
});

const frameworkStatus = ['SAME', 'DIFFERENT', 'LACK'];
const frameworkStatusDict = {
  SAME: '一致',
  DIFFERENT: '不一致',
  LACK: '缺失'
};
// 同名异构比对结果筛选项
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
    getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
  },
  onUpdatePageSize: (pageSize) => {
    frameworkPagination.pageSize = pageSize;
    frameworkPagination.page = 1;
    getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
  }
});

// 获取比对数据
function getData(qualityboardIdParam, roundCompareeIdParam, roundCurIdParam) {
  loading.value = true;
  // 软件范围比对
  if (packageTabValueFirst.value === 'softwarescope') {
    getPackageListComparationDetail(qualityboardIdParam, roundCompareeIdParam, roundCurIdParam, {
      compare_result_list: JSON.stringify(compareResultColumn.filterOptionValues),
      arches: JSON.stringify(archesParam.value),
      ...thisParams.value,
      page_num: softwarescopePagination.page,
      page_size: softwarescopePagination.pageSize
    })
      .then((res) => {
        packageChangeSummary.value.addPackagesNum = res.data.add_pkgs_num; // 新增
        packageChangeSummary.value.delPackagesNum = res.data.del_pkgs_num; // 减少
        softwarescopeTableData.value = res.data.items; // 表格数据
        softwarescopeTotalNum.value = res.data.total; // 总数
        softwarescopePagination.itemCount = res.data.total; // 总数
      })
      .finally(() => {
        loading.value = false;
      });
  } else {
    // 同名异构
    getHomonymousIsomerismPkgcompare(qualityboardIdParam, roundCurIdParam, {
      compare_result_list: JSON.stringify(frameworkCompareResultColumn.filterOptionValues),
      ...thisParams.value,
      page_num: frameworkPagination.page,
      page_size: frameworkPagination.pageSize
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
  softwarescopeTableData.value = [];
  frameworkDate.value = [];
  thisParams.value = {
    search: null,
    desc: false,
    repo_path: packageTabValueSecond
  };
  archesParam.value = ['aarch64', 'x86_64', 'noarch'];
  softwarescopeTotalNum.value = null;
  frameworktotalNum.value = null;
};

const buttonDisabled = ref(false); // 禁用重新比对

// 重新比对
function handleCreateClick(qualityboardIdParam, roundCompareeIdParam, roundCurIdParam, params) {
  buttonDisabled.value = true;
  window.$message?.loading('开始比对，请稍等');
  if (packageTabValueFirst.value === 'softwarescope') {
    setPackageListComparationDetail(qualityboardIdParam, roundCompareeIdParam, roundCurIdParam, params)
      .then(() => {
        window.$message?.success('比对成功');
        softwarescopePagination.page = 1;
        getData(qualityboardIdParam, roundCompareeIdParam, roundCurIdParam);
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
        frameworkPagination.page = 1;
        getData(qualityboardIdParam, roundCompareeIdParam, roundCurIdParam);
      })
      .catch(() => {
        window.$message?.error('比对失败');
      })
      .finally(() => {
        buttonDisabled.value = false;
      });
  }
}

// 软件范围筛选条件变化
const softwarescopeFiltersChange = (filters) => {
  compareResultColumn.filterOptionValues = filters.compare_result || [];
  softwarescopePagination.page = 1;
  getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
};

// 同名异构筛选条件变化
const frameworkFiltersChange = (filters) => {
  frameworkCompareResultColumn.filterOptionValues = filters.compare_result || [];
  frameworkPagination.page = 1;
  getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
};

// 导出比对结果
const exportPackageComparationFn = () => {
  axios
    .downLoad(`/v1/round/${roundCompareeId.value}/with/${roundCurId.value}/pkg-compare-result-export`, {
      repo_path: packageTabValueSecond.value,
      arches: JSON.stringify(archesParam.value)
    })
    .then((res) => {
      let blob = new Blob([res], { type: 'application/vnd.ms-excel' });
      let url = URL.createObjectURL(blob);
      let alink = document.createElement('a');
      document.body.appendChild(alink);
      alink.download = '比对结果';
      alink.target = '_blank';
      alink.href = url;
      alink.click();
      alink.remove();
      URL.revokeObjectURL(url);
    });
};

// 多版本软件包
const multiVersionPackageRef = ref(null);
const showMultiVersionPackage = () => {
  multiVersionPackageRef.value.showModal = true;
};

watch(
  thisParams,
  () => {
    softwarescopePagination.page = 1;
    frameworkPagination.page = 1;
    getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
  },
  { deep: true }
);

watch(archesParam, () => {
  softwarescopePagination.page = 1;
  frameworkPagination.page = 1;
  getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
});

watch(roundCurId, () => {
  softwarescopeTotalNum.value = null;
  frameworktotalNum.value = null;
  softwarescopeTableData.value = [];
  frameworkDate.value = [];
  softwarescopePagination.page = 1;
  frameworkPagination.page = 1;
  getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
});

watch(packageTabValueFirst, () => {
  softwarescopePagination.page = 1;
  frameworkPagination.page = 1;
  getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
});

watch(
  [oldPackage, newPackage],
  () => {
    compareeColumn.title = oldPackage.value.name; // 第一列名称
    comparerColumn.title = newPackage.value.name; // 第二列名称
  },
  { deep: true }
);

onMounted(() => {
  softwarescopePagination.page = 1;
  frameworkPagination.page = 1;
  getData(qualityboardId.value, roundCompareeId.value, roundCurId.value);
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
