import { h, ref, watch, nextTick } from 'vue';
import {
  getFeatureCompletionRates,
  getFeatureList as getFeatureData,
  getPackageListComparationSummaryAxios,
  getPackageListComparationDetail as getPackageChangeSummary
} from '@/api/get';
import { NButton, NTag, NSpace } from 'naive-ui';
import { list, currentId, preId } from './productTable';

const detail = ref({});
const drawerShow = ref(false);
const active = ref(false);
const requestCard = ref(null);
const cardDescription = ref({
  title: null,
  progress: null
});
function cardClick() {
  active.value = true;
}
const activeTab = ref('testProgress');
const testProgressList = ref([]);

const boxWidth = ref(0);

const oldPackage = ref({
  size: 0,
  name: null
});
const newPackage = ref({
  size: 0,
  name: null
});
const packageChangeSummary = ref({
  addPackagesNum: 0,
  delPackagesNum: 0
});

// 获取软件包变更数据
function getPackageListComparationSummary(qualityboardId, params) {
  const idList = list.value.map((item) => item.id);
  const currentIndex = idList.indexOf(currentId.value);
  if (currentIndex === 0) {
    // 暂时设为round1，未来设置为前正式发布版本的release里程碑
    preId.value = currentId.value;
    getPackageListComparationSummaryAxios(qualityboardId, currentId.value, {
      summary: true,
      refresh: params.refresh,
      repo_path: params.repoPath,
      arch: params.arch
    })
      .then((res) => {
        if (!params.refresh) {
          newPackage.value.size = res.data.size;
          newPackage.value.name = res.data.name;
          oldPackage.value.size = res.data.size;
          oldPackage.value.name = res.data.name;
          packageChangeSummary.value.addPackagesNum = 0;
          packageChangeSummary.value.delPackagesNum = 0;
        } else {
          window.$message?.info(res.error_msg, { duration: 8e3 });
        }
      })
      .catch(() => {
        window.$message?.warning('软件包列表数据缺失，请点击软件包范围变更卡片刷新按钮重新获取');
        oldPackage.value.size = '?';
        oldPackage.value.name = null;
        newPackage.value.size = '?';
        newPackage.value.name = null;
      });
  } else {
    preId.value = idList[currentIndex - 1];
    getPackageListComparationSummaryAxios(qualityboardId, preId.value, {
      summary: true,
      refresh: params.refresh,
      repo_path: params.repoPath,
      arch: params.arch
    })
      .then((res) => {
        if (!params.refresh) {
          oldPackage.value.size = res.data.size;
          oldPackage.value.name = res.data.name;
        } else {
          window.$message?.info(res.error_msg, { duration: 8e3 });
        }
      })
      .catch(() => {
        window.$message?.warning('前置软件包列表数据缺失，请点击软件包范围变更卡片刷新按钮重新获取');
        oldPackage.value.size = '?';
        oldPackage.value.name = null;
      });
    getPackageListComparationSummaryAxios(qualityboardId, currentId.value, {
      summary: true,
      refresh: params.refresh,
      repo_path: params.repoPath,
      arch: params.arch
    })
      .then((res) => {
        if (!params.refresh) {
          newPackage.value.size = res.data.size;
          newPackage.value.name = res.data.name;
        } else {
          window.$message?.info(res.error_msg, { duration: 8e3 });
        }
      })
      .catch(() => {
        window.$message?.warning('当前软件包列表数据缺失，请点击软件包范围变更卡片刷新按钮重新获取');
        newPackage.value.size = '?';
        newPackage.value.name = null;
      });
    getPackageChangeSummary(qualityboardId, preId.value, currentId.value, { summary: true, repo_path: params.repoPath })
      .then((res) => {
        packageChangeSummary.value.addPackagesNum = res.data.add_pkgs_num;
        packageChangeSummary.value.delPackagesNum = res.data.del_pkgs_num;
      })
      .catch(() => {
        packageChangeSummary.value.addPackagesNum = '?';
        packageChangeSummary.value.delPackagesNum = '?';
      });
  }
}

const showPackage = ref(false);
const packageBox = ref(null);
const packageWidth = ref(0);
watch(showPackage, () => {
  nextTick(() => {
    packageWidth.value = requestCard.value.$el.clientWidth;
  });
});

const featureListColumns = [
  {
    key: 'no',
    title: '编号',
    className: 'feature-no',
    render: (row) => {
      return h(
        NButton,
        {
          type: 'info',
          text: true,
          onClick: () => {
            window.open(row.url);
          }
        },
        row.no
      );
    }
  },
  {
    key: 'feature',
    title: '特性',
    className: 'feature-name'
  },
  {
    key: 'sig',
    title: '归属SIG',
    className: 'feature-sig',
    render: (row) => {
      return row.sig?.map((item) =>
        h(
          NButton,
          {
            type: 'info',
            text: true,
            style: {
              padding: '5px',
              display: 'block'
            },
            onClick: () => {}
          },
          item
        )
      );
    }
  },
  {
    key: 'owner',
    title: '责任人',
    className: 'feature-owner',
    render: (row) => {
      return row.owner?.map((item) =>
        h(
          NButton,
          {
            type: 'info',
            text: true,
            style: {
              padding: '5px',
              display: 'block'
            },
            onClick: () => {}
          },
          item
        )
      );
    }
  },
  {
    key: 'release-to',
    title: '发布方式',
    className: 'feature-release-to'
  },
  {
    key: 'pkgs',
    title: '影响软件包范围',
    className: 'feature-pkgs',
    render: (row) => {
      return h(
        NSpace,
        {},
        row.pkgs?.map((item) => h(NTag, {}, item))
      );
    }
  },
  {
    key: 'status',
    title: '特性状态',
    className: 'feature-task-status'
  }
];

const additionFeatureSummary = ref({});
const inheritFeatureSummary = ref({});

const featureLoading = ref(false);
const featureListData = ref([]);
const showList = ref(false);

function handleListClick() {
  showList.value = true;
}

function getFeatureList(qualityboardId, _type) {
  featureLoading.value = true;
  getFeatureData(qualityboardId, { new: _type === 'addition' })
    .then((res) => {
      featureListData.value = res.data;
    })
    .finally(() => {
      featureLoading.value = false;
    });
}

function getFeatureSummary(qualityboardId) {
  getFeatureCompletionRates(qualityboardId).then((res) => {
    additionFeatureSummary.value = res.data.addition_feature_summary;
    inheritFeatureSummary.value = res.data.inherit_feature_summary;
  });
}

function cleanFeatureListData() {
  featureLoading.value = false;
  featureListData.value = [];
}
function cleanPackageListData() {
  packageChangeSummary.value = {
    addPackagesNum: 0,
    delPackagesNum: 0
  };
  newPackage.value = {};
  oldPackage.value = {};
}

watch(showList, () => {
  nextTick(() => {
    boxWidth.value = requestCard.value.$el.clientWidth;
  });
});

export {
  packageBox,
  showPackage,
  requestCard,
  newPackage,
  showList,
  oldPackage,
  packageWidth,
  boxWidth,
  additionFeatureSummary,
  inheritFeatureSummary,
  activeTab,
  active,
  detail,
  testProgressList,
  drawerShow,
  cardDescription,
  cardClick,
  handleListClick,
  getFeatureSummary,
  cleanFeatureListData,
  cleanPackageListData,
  getFeatureList,
  featureListColumns,
  featureListData,
  featureLoading,
  getPackageListComparationSummary,
  packageChangeSummary
};
