import { h, ref } from 'vue';
import { getPackageListComparationDetail } from '@/api/get';
import { oldPackage, newPackage } from '@/views/versionManagement/product/modules/productDetailDrawer';

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

const columns = ref([
  {
    key: 'rpm_list_1',
  },
  {
    key: 'rpm_list_2',
  },
  {
    key: 'compare_result',
    title: '比对结果',
    filterOptions: rpmCompareStatusOptions,
    filter (value, row) {
      return row.compare_result === value;
    },
    render: (row) => {
      return h(
        'span',
        {},
        rpmCompareStatusDict[row.compare_result]
      );
    }
  },
]);

const loading = ref(false);
const nativeData = ref([]);
const data = ref([]);

function getData (qualityboardId, milestonePreId, milestoneCurId) {
  loading.value = true;
  getPackageListComparationDetail(qualityboardId, milestonePreId, milestoneCurId)
    .then((res) => {
      columns.value[0].title = oldPackage.value.name;
      columns.value[1].title = newPackage.value.name;
      nativeData.value = res.data;
      if (milestoneCurId === milestonePreId) {
        nativeData.value.forEach((item) => {
          item.rpm_list_1 = null;
          item.compare_result = null;
        });
      }
      data.value = nativeData.value;
      loading.value = false;
    });
}

const cleanData = () => {
  loading.value = false;
  nativeData.value = [];
  data.value = [];
};

function handleInput(value) {
  data.value = nativeData.value.filter((item) => {
    return item.rpm_list_1.includes(value) || item.rpm_list_2.includes(value);
  });
}

export {
  loading,
  data,
  getData,
  cleanData,
  columns,
  searchValue,
  handleInput,
};
