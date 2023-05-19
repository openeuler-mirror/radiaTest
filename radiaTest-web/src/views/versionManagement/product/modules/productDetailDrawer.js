import { h, ref, watch, nextTick } from 'vue';
import { NButton, NTag, NSpace } from 'naive-ui';
import {
  getFeatureCompletionRates,
  getFeatureList as getFeatureData,
  getPackageListComparationSummaryAxios,
  getPackageListComparationDetail as getPackageChangeSummary,
  getProduct,
  getAllMilestone
} from '@/api/get';
import { updateCompareRounds } from '@/api/put';
import {
  list,
  currentId,
  currentRound,
  dashboardId,
  packageTabValueFirst,
  packageTabValueSecond
} from './productTable';

const drawerShow = ref(false); // 显示质量看板抽屉
const detail = ref({}); // 产品版本详情
const roundCompareeId = ref(''); // 对比roundId
const requestCard = ref(null); // 特性及软件包包裹ref

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
const hasMultiVersionPackage = ref(false); // 是否有多版本软件包

// 获取软件包变更对比卡片数据
function getPackageListComparationSummary(qualityboardId, params) {
  oldPackage.value = {
    size: 0,
    name: null
  };
  newPackage.value = {
    size: 0,
    name: null
  };
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
          if (res.data?.repeat_rpm_cnt > 0) {
            hasMultiVersionPackage.value = true;
          }
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
          if (res.data?.repeat_rpm_cnt > 0) {
            hasMultiVersionPackage.value = true;
          }
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
          if (res.data?.repeat_rpm_cnt > 0) {
            hasMultiVersionPackage.value = true;
          }
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

// 清空对比卡片数据
function cleanPackageListData() {
  packageChangeSummary.value = {
    addPackagesNum: 0,
    delPackagesNum: 0
  };
  newPackage.value = {
    size: 0,
    name: null
  };
  oldPackage.value = {
    size: 0,
    name: null
  };
}

const showPackage = ref(false); // 显示软件包变更详情
const currentPanel = ref('fixed'); // 当前软件包对比tab
const packageComparePanels = ref([
  {
    name: '上轮迭代',
    id: 'fixed'
  }
]);
const showAddNewCompare = ref(false); // 新增比对弹框
const productOptions = ref([]); // 新增比对产品版本选项
const productLoading = ref(false);
const roundOptions = ref([]); // 新增比对迭代选项
const roundLoading = ref(false);
// 新增比对表单
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
  updateCompareRounds(
    currentId.value,
    {
      comparee_round_ids: [...currentRound.value.comparee_round_ids.map((item) => item.id), newCompareForm.value.round]
    },
    { successMsg: '添加成功' }
  )
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

  updateCompareRounds(
    currentId.value,
    { comparee_round_ids: panelList.map((item) => item.id) },
    { successMsg: '删除成功' }
  ).then((res) => {
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

// 新增比对modal显示/隐藏回调
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

        if (newCompareForm.value.type === 'release') {
          newCompareForm.value.round = roundOptions.value[0]?.value;
        } else {
          newCompareForm.value.round = null;
        }
      })
      .finally(() => {
        roundLoading.value = false;
      });
  }
);

watch(currentPanel, () => {
  packageTabValueFirst.value = 'softwarescope';
  packageTabValueSecond.value = 'everything';
  getPackageListComparationSummary(dashboardId.value, {
    refresh: false,
    repoPath: packageTabValueSecond.value,
    arch: 'all'
  });
});

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

const showList = ref(false); // 显示新增/继承特性详情
const boxWidth = ref(0); // 特性卡片宽度
const additionFeatureSummary = ref({}); // 新增特性总结
const inheritFeatureSummary = ref({}); // 继承特性总结
const featureLoading = ref(false);
const featureListData = ref([]);
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

// 点击特性卡片
function handleListClick() {
  showList.value = true;
}

// 获取特性表格数据
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

// 获取特性总结数据
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

watch(showList, () => {
  nextTick(() => {
    boxWidth.value = requestCard.value.$el.clientWidth;
  });
});

const active = ref(false); // milestoneIssuesCard弹窗

// 点击问题解决卡片
function cardClick() {
  active.value = true;
}

const activeTab = ref('testProgress'); // 质量看板下方激活模板

// 每日构建弹框
const createDailyBuildRef = ref(null);
const showDailyBuildModal = () => {
  createDailyBuildRef.value.showModal = true;
};

export {
  createDailyBuildRef,
  showDailyBuildModal,
  showPackage,
  requestCard,
  newPackage,
  showList,
  oldPackage,
  boxWidth,
  additionFeatureSummary,
  inheritFeatureSummary,
  activeTab,
  active,
  detail,
  drawerShow,
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
  roundCompareeId,
  hasMultiVersionPackage
};
