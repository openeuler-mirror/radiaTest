import { h, ref, reactive } from 'vue';
import { getPackageListComparationDetail } from '@/api/get';
import { setPackageListComparationDetail } from '@/api/post';
import { oldPackage, newPackage, packageChangeSummary } from '@/views/versionManagement/product/modules/productDetailDrawer';

const searchValue = ref('');

const rpmCompareStatus = [
  'SAME',
  'VER_UP',
  'VER_DOWN',
  'REL_UP',
  'REL_DOWN',
  'ADD',
  'DEL',
  'ERROR'
];

const rpmCompareStatusDict = {
  SAME: '一致',
  VER_UP: '版本号升级',
  VER_DOWN: '版本号降级',
  REL_UP: 'release号升级',
  REL_DOWN: 'release号降级',
  ADD: '新增',
  DEL: '移除',
  ERROR: '比对异常',
};

const rpmCompareStatusOptions = rpmCompareStatus.map((item) => {
  return {
    label: rpmCompareStatusDict[item],
    value: item,
  };
});

const compareeColumn = reactive({
  key: 'rpm_comparee',
});
const comparerColumn = reactive({
  key: 'rpm_comparer',
});
const compareResultColumn = reactive({
  key: 'compare_result',
  title: '比对结果',
  className: 'compare-result',
  filter: true,
  filterOptionValues: [],
  filterOptions: rpmCompareStatusOptions,
  render: (row) => {
    return h(
      'span',
      {},
      rpmCompareStatusDict[row.compare_result]
    );
  }
});

const columns = [
  compareeColumn,
  comparerColumn,
  compareResultColumn
];

const loading = ref(false);
const data = ref([]);
const totalNum = ref(null);
const archesParam = ref(['aarch64', 'x86_64', 'noarch']);
const thisParams = ref({
  search: null,
  desc: false,
  page_num: 1,
  page_size: 10,
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

function getData (qualityboardId, milestonePreId, milestoneCurId) {
  loading.value = true;
  getPackageListComparationDetail(
    qualityboardId, 
    milestonePreId, 
    milestoneCurId, 
    {
      compare_result_list: JSON.stringify(compareResultColumn.filterOptionValues),
      arches: JSON.stringify(archesParam.value),
      ...thisParams.value
    }
  )
    .then((res) => {
      compareeColumn.title = oldPackage.value.name;
      comparerColumn.title = newPackage.value.name;
      data.value = res.data.items;
      totalNum.value = res.data.total;
      pagination.itemCount = res.data.total;
      packageChangeSummary.value.addPackagesNum = res.data.add_pkgs_num;
      packageChangeSummary.value.delPackagesNum = res.data.del_pkgs_num;
      if (milestoneCurId === milestonePreId) {
        data.value.forEach((item) => {
          item.rpm_comparee = null;
          item.compare_result = null;
        });
        packageChangeSummary.value.addPackagesNum = 0;
        packageChangeSummary.value.delPackagesNum = 0;
      }
    })
    .finally(() => { loading.value = false; });
}

const cleanData = () => {
  loading.value = false;
  data.value = [];
  thisParams.value = {
    search: null,
    desc: false,
    page_num: 1,
    page_size: 10,
  };
  archesParam.value = ['aarch64', 'x86_64', 'noarch'];
  totalNum.value = null;
};

const buttonDisabled = ref(false);

function handleCreateClick (qualityboardId, milestonePreId, milestoneCurId) {
  buttonDisabled.value = true;
  window.$message?.loading('开始比对，请稍等');
  setPackageListComparationDetail(qualityboardId, milestonePreId, milestoneCurId)
    .then(() => {
      window.$message?.success('比对成功');
      getData(qualityboardId, milestonePreId, milestoneCurId);
    })
    .catch(() => {
      window.$message?.error('比对失败');
    })
    .finally(() => {
      buttonDisabled.value = false;
    });
}

export {
  loading,
  data,
  getData,
  cleanData,
  columns,
  searchValue,
  thisParams,
  handleCreateClick,
  buttonDisabled,
  totalNum,
  pagination,
  archesParam,
  compareResultColumn,
};
