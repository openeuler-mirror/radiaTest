import { h, ref, watch, nextTick } from 'vue';
import {
  getFeatureCompletionRates,
  getFeatureList as getFeatureData,
  getPackageListComparationSummaryAxios,
  getPackageListComparationDetail as getPackageChangeSummary,
  getProduct,
  getAllMilestone
} from '@/api/get';
import { updateCompareRounds } from '@/api/put';
import { NButton, NTag, NSpace } from 'naive-ui';
import { list, currentId, currentRound, dashboardId, packageTabValueSecond } from './productTable';

const roundCompareeId = ref(''); // 对比roundId
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

const currentPanel = ref('fixed'); // 当前软件包对比tab

// 获取软件包变更数据
function getPackageListComparationSummary(qualityboardId, params) {
  const idList = list.value.map((item) => item.id); // roundId列表
  const currentIndex = idList.indexOf(currentRound.value.id);
  if (currentIndex === 0 && currentPanel.value === 'fixed') {
    roundCompareeId.value = currentId.value;
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
    if (currentPanel.value === 'fixed') {
      roundCompareeId.value = idList[currentIndex - 1];
    } else {
      roundCompareeId.value = currentPanel.value;
    }
    getPackageListComparationSummaryAxios(qualityboardId, roundCompareeId.value, {
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
    getPackageChangeSummary(qualityboardId, roundCompareeId.value, currentId.value, {
      summary: true,
      repo_path: params.repoPath
    })
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

const showPackage = ref(false); // 显示软件包变更详情
const packageBox = ref(null);
const packageWidth = ref(0);
watch(showPackage, () => {
  nextTick(() => {
    packageWidth.value = requestCard.value.$el.clientWidth;
  });
});

watch(currentPanel, () => {
  getPackageListComparationSummary(dashboardId.value, {
    refresh: false,
    repoPath: packageTabValueSecond.value,
    arch: 'all'
  });
});

const packageComparePanels = ref([
  {
    name: '上轮迭代',
    id: 'fixed'
  }
]);

watch(currentRound, () => {
  packageComparePanels.value = [
    {
      name: '上轮迭代',
      id: 'fixed'
    },
    ...currentRound.value.comparee_round_ids
  ];
  currentPanel.value = 'fixed';
});

const showAddNewCompare = ref(false);

const productOptions = ref([]);
const productLoading = ref(false);
const roundOptions = ref([]);
const roundLoading = ref(false);

// 软件包对比tab新增表单
const newCompareForm = ref({
  product: undefined,
  type: 'release',
  round: undefined
});

// 软件包对比tab是否可关闭
const packageCompareClosable = computed(() => {
  return packageComparePanels.value.length > 1;
});

// 显示软件包对比tab增加表单
function handlePackageCompareAdd() {
  showAddNewCompare.value = true;
}

// 新增软件包对比tab
function handleNewCompareCreate() {
  updateCompareRounds(currentId.value, {
    comparee_round_ids: [...currentRound.value.comparee_round_ids.map((item) => item.id), newCompareForm.value.round]
  })
    .then((res) => {
      packageComparePanels.value = [
        {
          name: '上轮迭代',
          id: 'fixed'
        },
        ...res.data.comparee_round_ids
      ];
      currentRound.value.comparee_round_ids = res.data.comparee_round_ids;
    })
    .finally(() => {
      showAddNewCompare.value = false;
    });
}

// 删除软件包对比tab
function handlePackageCompareClose(id) {
  const { value: panelList } = packageComparePanels;
  const closeIndex = panelList.findIndex((panel) => panel.id === id);
  if (closeIndex === 0) {
    window.$message?.error('默认比对项无法关闭');
    return;
  } else if (!~closeIndex) {
    return;
  }

  panelList.splice(closeIndex, 1);
  if (panelList[0]?.id === 'fixed') {
    panelList.splice(0, 1);
  }

  updateCompareRounds(currentId.value, { comparee_round_ids: panelList.map((item) => item.id) }).then((res) => {
    packageComparePanels.value = [
      {
        name: '上轮迭代',
        id: 'fixed'
      },
      ...res.data.comparee_round_ids
    ];
    currentPanel.value = 'fixed';
    currentRound.value.comparee_round_ids = res.data.comparee_round_ids;
  });
}

// 新增比对modal回调
watch(showAddNewCompare, () => {
  if (showAddNewCompare.value) {
    const params = {
      paged: false
    };
    productLoading.value = true;
    getProduct(params)
      .then((res) => {
        productOptions.value = res.data?.items?.map((item) => {
          return {
            label: `${item.name}-${item.version}`,
            value: item.id
          };
        });
      })
      .finally(() => {
        productLoading.value = false;
      });
  } else {
    newCompareForm.value = {
      product: undefined,
      type: 'release',
      round: undefined
    };
    productOptions.value = [];
    roundOptions.value = [];
  }
});

// 根据版本和类型获取round列表
watch(
  () => [newCompareForm.value.type, newCompareForm.value.product],
  () => {
    newCompareForm.value.round = undefined;
    const params = {
      paged: false,
      type: newCompareForm.value.type,
      product_id: newCompareForm.value.product
    };
    roundLoading.value = true;
    getAllMilestone(params)
      .then((res) => {
        roundOptions.value = res.data?.items?.map((item) => {
          return {
            label: item.name,
            value: item.round_id
          };
        });
        roundOptions.value = roundOptions.value.filter((item) => item.value);
      })
      .finally(() => {
        roundLoading.value = false;
      });
  }
);

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
    key: 'release_to',
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
const showList = ref(false); // 显示新增/继承特性详情

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
  packageChangeSummary,
  packageComparePanels,
  packageCompareClosable,
  handlePackageCompareAdd,
  handlePackageCompareClose,
  newCompareForm,
  showAddNewCompare,
  currentPanel,
  handleNewCompareCreate,
  productLoading,
  productOptions,
  roundLoading,
  roundOptions,
  roundCompareeId
};
