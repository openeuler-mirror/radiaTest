import {NIcon, NTag} from 'naive-ui';
import {CancelFilled, CancelRound, CheckCircleFilled} from '@vicons/material';
import {QuestionCircle16Filled} from '@vicons/fluent';
import {nextTick, ref, watch} from 'vue';
import {
  getBranchList,
  getChecklistResult,
  getFeatureCompletionRates,
  getMilestoneRate,
  getMilestones,
  getPackageListComparationDetail as getPackageChangeSummary,
  getPackageListComparationSummaryAxios,
  getProduct,
  getProductMessage,
  getRoundIssueRate,
  getAllMilestone, getRoundIdList,
} from '@/api/get';
import {createProductMessage} from '@/api/post';
import {milestoneNext, milestoneRollback, updateCompareRounds,} from '@/api/put';
import {CheckCircle} from '@vicons/fa';

import axios from '@/axios';
const productId = ref(null);
const boxWidth = ref(0); // 特性卡片宽度
const additionFeatureSummary = ref({}); // 新增特性总结
const inheritFeatureSummary = ref({}); // 继承特性总结
const showPackage = ref(false); // 显示软件包变更详情
const hasQualityboard = ref(false); // 是否有质量看板
const showList = ref(false); // 显示新增/继承特性详情
const tableLoading = ref(false); // 产品版本表格加载状态
const tableData = ref([]); // 产品版本表格数据
const dashboardId = ref(null); // 质量看板ID
const showChecklistBoard = ref(false); // round检查项比对结果弹框
const checklistBoardTableLoading = ref(false);
const checklistBoardTablePagination = ref({
  page: 1,
  pageSize: 5, // 受控模式下的分页大小
  pageCount: 1, // 总页数
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const productVersionPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const productList = ref([]); // 产品版本列表
const currentProduct = ref(''); // checklist选中产品版本
const checklistBoardTableData = ref([]);
const checklistBoardTablePageChange = (page) => {
  checklistBoardTablePagination.value.page = page;
};

const checklistBoardTablePageSizeChange = (pageSize) => {
  checklistBoardTablePagination.value.page = 1;
  checklistBoardTablePagination.value.pageSize = pageSize;
};
const showRoundMilestoneBoard = ref(false); // round关联里程碑弹框

// 点击round的milestone图表
const handleMilestone = () => {
  showRoundMilestoneBoard.value = true;
};
const oldPackage = ref({
  size: 0,
  name: null
});
const newPackage = ref({
  size: 0,
  name: null
});
const roundId = ref({});
const roundIdOptions = ref([]);
const loadingRef = ref(false);
const exportQualityHistoryFn = () => {
  loadingRef.value = true;
  let axiosUrl = `/v1/qualityboard/${productId.value}/report`;
  let param = {
    round_id: roundId.value.id || null,
    branch: branch.value.id || null
  };
  let tag = 'report';
  axios.downLoad(axiosUrl, param, tag).then((res) => {
    let blob = new Blob([res.data], { type: 'application/vnd.ms-excel' });
    let url = URL.createObjectURL(blob);
    let alink = document.createElement('a');
    document.body.appendChild(alink);
    alink.download = decodeURIComponent(res.headers['content-disposition'].split('=')[2].slice(7));
    alink.target = '_blank';
    alink.href = url;
    alink.click();
    alink.remove();
    URL.revokeObjectURL(url);
    loadingRef.value = false;
  }).catch(()=>{
    loadingRef.value = false;
  });
};
// 产品版本表格列
const columns = [
  {
    key: 'name',
    title: '产品',
    align: 'center',
  },
  {
    key: 'version',
    align: 'center',
    title: '版本',
  },
  {
    key: 'description',
    align: 'center',
    title: '描述'
  },
  {
    key: 'start_time',
    align: 'center',
    title: '开始时间'
  },
  {
    key: 'end_time',
    align: 'center',
    title: '结束时间'
  },
  {
    key: 'publish_time',
    align: 'center',
    title: '发布时间'
  },
  {
    key: 'current_resolved_rate',
    align: 'center',
    className: 'resolvedRate',
    title: '版本问题解决率',
    render(row) {
      if (row.current_resolved_passed === true) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false
          },
          {
            default: row.current_resolved_rate,
            icon: () =>
              h(NIcon, {
                component: CheckCircleFilled
              })
          }
        );
      } else if (row.current_resolved_passed !== false) {
        return h(
          NTag,
          {
            type: 'default',
            round: true,
            bordered: false
          },
          {
            default: 'unknown',
            icon: () =>
              h(NIcon, {
                component: QuestionCircle16Filled
              })
          }
        );
      }
      return h(
        NTag,
        {
          type: 'error',
          round: true,
          bordered: false
        },
        {
          default: row.current_resolved_rate,
          icon: () =>
            h(NIcon, {
              component: CancelRound
            })
        }
      );
    }
  },
  {
    key: 'serious_main_resolved_rate',
    align: 'center',
    className: 'seriousMain',
    title: '严重/主要问题解决率',
    render(row) {
      if (row.serious_main_resolved_passed === true) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false
          },
          {
            default: row.serious_main_resolved_rate,
            icon: () =>
              h(NIcon, {
                component: CheckCircleFilled
              })
          }
        );
      } else if (row.serious_main_resolved_passed !== false) {
        return h(
          NTag,
          {
            type: 'default',
            round: true,
            bordered: false
          },
          {
            default: 'unknown',
            icon: () =>
              h(NIcon, {
                component: QuestionCircle16Filled
              })
          }
        );
      }
      return h(
        NTag,
        {
          type: 'error',
          round: true,
          bordered: false
        },
        {
          default: row.serious_main_resolved_rate,
          icon: () =>
            h(NIcon, {
              component: CancelRound
            })
        }
      );
    }
  },
];
const productFilterParam = ref({
  name: null,
  version: null,
  description: null,
  start_time: null,
  end_time: null,
  publish_time: null
});
const productVersionPageChange = (page) => {
  productVersionPagination.value.page = page;
  getVersionTableData({
    ...productFilterParam.value,
    page_num: productVersionPagination.value.page,
    page_size: productVersionPagination.value.pageSize
  });
};

const productVersionPageSizeChange = (pageSize) => {
  productVersionPagination.value.pageSize = pageSize;
  productVersionPagination.value.page = 1;
  getVersionTableData({
    ...productFilterParam.value,
    page_num: productVersionPagination.value.page,
    page_size: productVersionPagination.value.pageSize
  });
};
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
const newCompareForm = ref({
  product: undefined,
  type: 'release',
  round: undefined
});
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
const detail = ref({}); // 产品版本详情
const getVersionTableData=(param)=>{
  tableLoading.value = true;
  getProduct(param)
    .then((res) => {
      tableData.value = res.data.items || [];
      tableLoading.value = false;
      productVersionPagination.value.pageCount = res.data.pages;
      productVersionPagination.value.page = res.data.current_page;
      productVersionPagination.value.pageSize = res.data.page_size;
    })
    .catch(() => {
      tableLoading.value = false;
    });
};
// 获取branches下拉列表
const branchOptions = ref([]);
const branch = ref({});
const getBranchSelectList = (product) => {
  branch.value = ref({name: '选择分支', id: null });
  branchOptions.value = [];
  let branchList = [];
  getBranchList(product, {round_id : roundId.value.id} ).then((res) => {
    res.data.length && res.data.forEach((item) => {
      branchList.push({
        label: item,
        value: { name: item, id: item }
      });
    });
    branchList.unshift({
      label: '选择分支',
      value: {name: '选择分支', id: null }
    });
    branchOptions.value = branchList;
  });
};
const list = ref([]);
const done = ref(false);
const currentId=ref();
const currentRound = ref({}); // 当前round信息
const resolvedMilestone = ref({}); // 问题解决统计迭代/里程碑
const resolvedMilestoneOptions = ref([]);
const defaultMilestoneId = ref(null); // 测试进展默认里程碑
const packageTabValueFirst = ref('softwarescope');
const packageTabValueSecond = ref('everything');
const seriousResolvedRate = ref(null); // 严重问题解决率

const seriousResolvedPassed = ref(null); // 严重问题解决率检查项

const mainResolvedRate = ref(null); // 主要问题解决率
const mainResolvedPassed = ref(null); // 主要问题解决率检查项

const seriousMainResolvedRate = ref(null); // 严重主要问题解决率
const seriousMainResolvedPassed = ref(null); // 严重主要问题解决率检查项

const currentResolvedRate = ref(null); // 当前迭代问题解决率
const currentResolvedPassed = ref(null); // 当前迭代问题解决率检查项

const leftIssuesPassed = ref(null); // 遗留问题解决率检查项

const seriousMainResolvedCnt = ref(null); // 严重主要问题解决数
const seriousMainAllCnt = ref(null); // 严重主要问题总数

const currentResolvedCnt = ref(null); // 当前迭代问题解决数
const currentAllCnt = ref(null); // 当前迭代问题总数

const leftIssuesCnt = ref(null); // 遗留问题数

const issuesResolvedPassed = ref(null); // 问题解决是否达标
// const showPackage = ref(false); // 显示软件包变更详情
const currentPanel = ref('fixed'); // 当前软件包对比tab
watch(
  [currentResolvedPassed, seriousMainResolvedPassed, seriousResolvedPassed, mainResolvedPassed, leftIssuesPassed],
  () => {
    let passedList = [
      currentResolvedPassed.value,
      seriousMainResolvedPassed.value,
      seriousResolvedPassed.value,
      mainResolvedPassed.value,
      leftIssuesPassed.value
    ];
    if (passedList.filter((item) => item === false).length > 0) {
      issuesResolvedPassed.value = false;
    } else if (passedList.filter((item) => item === true).length === 0) {
      issuesResolvedPassed.value = null;
    } else {
      issuesResolvedPassed.value = true;
    }
  }
);
const currentPanelDetail = ref({}); // 当前软件包对比tab详细
const requestCard = ref(null); // 特性及软件包包裹ref

// 更改软件包比对tab
watch(currentPanel, () => {
  packageTabValueFirst.value = 'softwarescope';
  packageTabValueSecond.value = 'everything';
  currentPanelDetail.value = packageComparePanels.value.find((item) => {
    return item.id === currentPanel.value;
  });
  getPackageListComparationSummary(dashboardId.value, {
    refresh: false,
    repoPath: packageTabValueSecond.value,
    arch: 'all'
  });
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
watch(showList, () => {
  nextTick(() => {
    boxWidth.value = requestCard.value.$el.clientWidth;
  });
});
const setResolvedData = (rateData) => {
  for (let i in rateData) {
    if (rateData[i] === null) {
      rateData[i] = 0;
    }
    if (rateData[i] !== 0 && i.includes('_rate')) {
      rateData[i] = rateData[i].toString().substring(0, rateData[i].length - 1);
    }
  }
  seriousResolvedRate.value = rateData.serious_resolved_rate;
  seriousResolvedPassed.value = rateData.serious_resolved_passed;
  mainResolvedRate.value = rateData.main_resolved_rate;
  mainResolvedPassed.value = rateData.main_resolved_passed;
  seriousMainAllCnt.value = rateData.serious_main_all_cnt;
  seriousMainResolvedCnt.value = rateData.serious_main_resolved_cnt;
  seriousMainResolvedRate.value = rateData.serious_main_resolved_rate;
  seriousMainResolvedPassed.value = rateData.serious_main_resolved_passed;
  currentResolvedCnt.value = rateData.current_resolved_cnt;
  currentAllCnt.value = rateData.current_all_cnt;
  currentResolvedRate.value = rateData.current_resolved_rate;
  currentResolvedPassed.value = rateData.current_resolved_passed;
  leftIssuesCnt.value = rateData.left_issues_cnt;
  leftIssuesPassed.value = rateData.left_issues_passed;
};
const getRoundRelateMilestones = (round) => {
  getMilestones({ round_id: round, paged: false }).then((res) => {
    resolvedMilestoneOptions.value = [{ label: '当前迭代', value: { name: '当前迭代', id: currentRound.value.id } }];
    defaultMilestoneId.value = res.data.items[0]?.round_info?.default_milestone_id;
    res.data.items.forEach((item) => {
      resolvedMilestoneOptions.value.push({
        label: item.name,
        value: { name: item.name, id: item.id }
      });
    });
  });
};
const getRoundSelectList = (product) => {
  roundId.value = ref({name: '选择round', id: null });
  let roundList = [];
  getRoundIdList(product).then((res) => {
    res.data.length && res.data.forEach((item) => {
      roundList.push({
        label: item.name,
        value: { name: item.name, id: item.id }
      });
    });
    roundList.unshift({
      label: '选择round',
      value: { name: '选择round', id: null }
    });
    roundIdOptions.value = roundList;
  });
};
const selectResolvedMilestone = (value) => {
  if (value.name === '当前迭代') {
    getRoundIssueRate(value.id).then((res) => {
      setResolvedData(res.data);
    });
  } else {
    getMilestoneRate(value.id).then((res) => {
      setResolvedData(res.data);
    });
  }
};
function dynamicAnimateCss(elementsClass, animationCssClass) {
  const elements = document.querySelectorAll(`.${elementsClass}`);
  elements.forEach((el) => {
    el.classList.add('animate__animated', animationCssClass);
    el.addEventListener(
      'animationend',
      () => {
        el.classList.remove('animate__animated', animationCssClass);
      },
      { once: true }
    );
  });
}
function handleClick(item) {
  if (item.id > currentId.value) {
    dynamicAnimateCss('inout-animated', 'animate__fadeInRight');
  } else {
    dynamicAnimateCss('inout-animated', 'animate__fadeInLeft');
  }
  packageTabValueFirst.value = 'softwarescope';
  packageTabValueSecond.value = 'everything';
  currentRound.value = item;
  currentId.value = item.id;
  resolvedMilestone.value = { name: '当前迭代', id: item.id };
  getRoundRelateMilestones(item.id);
  getRoundIssueRate(item.id).then((res) => {
    const rateData = res.data;
    setResolvedData(rateData);
  });
  getPackageCardData(packageTabValueFirst.value);
}
function getDefaultCheckNode(id) {
  getProductMessage(id)
    .then((res) => {
      dashboardId.value = res.data[0].id;
      hasQualityboard.value = true;
      const rateData = res.data[0].current_round_issue_solved_rate;
      setResolvedData(rateData);
      currentId.value = res.data[0].current_round_id;
      const newArr = Object.keys(res.data[0].rounds).map((item) => {
        const thisRoundData = {
          id: item,
          name: res.data[0].rounds[item].name,
          type: res.data[0].rounds[item].type,
          product_id: res.data[0].rounds[item].product_id,
          comparee_round_ids: res.data[0].rounds[item].comparee_round_ids,
          default_milestone_id: res.data[0].rounds[item].default_milestone_id
        };
        if (item === currentId.value) {
          currentRound.value = thisRoundData;
        }
        return thisRoundData;
      });
      resolvedMilestone.value = { name: '当前迭代', id: currentRound.value.id };
      list.value = newArr;
      tableLoading.value = false;
      if (newArr.length > 0) {
        done.value = newArr.at(-1).type === 'release';
        getFeatureSummary(dashboardId.value);
        getPackageListComparationSummary(dashboardId.value, {
          refresh: false,
          repoPath: packageTabValueSecond.value,
          arch: 'all'
        });
        getRoundRelateMilestones(currentRound.value.id);
      }
    })
    .catch(() => {
      hasQualityboard.value = false;
      list.value = [];
      tableLoading.value = false;
    });
}
// 开启下一轮迭代测试
function stepAdd() {
  if (hasQualityboard.value === false) {
    createProductMessage(productId.value)
      .then(() => {
        window.$message?.info('已创建qualityboard');
        getDefaultCheckNode(productId.value);
      })
      .catch(() => {
        window.$message?.info('创建qualityboard失败');
      })
      .finally(() => {
        tableLoading.value = false;
      });
  } else {
    tableLoading.value = true;
    milestoneNext(dashboardId.value, { released: false })
      .then((res) => {
        if (res.error_code === '2000') {
          list.value = Object.keys(res.data.rounds).map((item) => ({
            id: item,
            name: res.data.rounds[item].name,
            type: res.data.rounds[item].type,
            product_id: res.data.rounds[item].product_id
          }));
          currentId.value = res.data.current_round_id;
          window.$message.success('迭代已转测');
        } else {
          window.$message.error('迭代转测失败');
        }
      })
      .finally(() => {
        tableLoading.value = false;
      });
  }
}

// 回退至上一迭代
function handleRollback(recovery = false) {
  milestoneRollback(dashboardId.value)
    .then(() => {
      getDefaultCheckNode(productId.value);
      if (recovery) {
        window.$message?.success('当前进展已回退最后一轮迭代');
        done.value = false;
      } else {
        window.$message?.success('当前进展已回退至上一轮迭代');
      }
    })
    .catch(() => {
      window.$message?.error('回退失败');
    });
}

// 发布
function haveDone() {
  tableLoading.value = true;
  milestoneNext(dashboardId.value, { released: true })
    .then((res) => {
      if (res.error_code === '2000') {
        list.value = Object.keys(res.data.rounds).map((item) => ({
          id: item,
          name: res.data.rounds[item].name,
          type: res.data.rounds[item].type,
          product_id: res.data.rounds[item].product_id
        }));
        currentId.value = res.data.current_round_id;
        done.value = true;
        window.$message.success('已正式发布');
      } else {
        window.$message.error('发布失败');
      }
      tableLoading.value = false;
      getDefaultCheckNode(productId.value);
    })
    .catch(() => {
      window.$message.error('发布失败');
      done.value = false;
      tableLoading.value = false;
    });
}

// 取消发布，恢复至最后一轮迭代
function haveRecovery() {
  handleRollback(true);
}
// 软件范围获取对比卡片数据
const getPackageCardData = (type) => {
  if (type === 'softwarescope') {
    getPackageListComparationSummary(dashboardId.value, {
      refresh: false,
      repoPath: packageTabValueSecond.value,
      arch: 'all'
    });
  }
};

// 切换软件范围/同名异构
const roundCompareeId = ref(''); // 对比roundId
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
function getFeatureSummary(qualityboardId) {
  getFeatureCompletionRates(qualityboardId).then((res) => {
    additionFeatureSummary.value = res.data.addition_feature_summary;
    inheritFeatureSummary.value = res.data.inherit_feature_summary;
  });
}

const handleChecklistBoard = () => {
  showChecklistBoard.value = true;
  checklistBoardTableLoading.value = true;
  getChecklistResult(currentRound.value.id).then((res) => {
    checklistBoardTableLoading.value = false;
    checklistBoardTableData.value = [];
    res.data?.forEach((v) => {
      checklistBoardTableData.value.push({
        check_item: v.title,
        baseline: v.baseline,
        operation: v.operation,
        currentValue: v.current_value,
        result: v.compare_result
      });
    });
  });
};
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
const updateRoundMilestoneBoard = (value) => {
  if (!value) {
    getRoundRelateMilestones(currentRound.value.id);
    resolvedMilestone.value = { name: '当前迭代', id: currentRound.value.id };
    getRoundIssueRate(currentRound.value.id).then((res) => {
      const rateData = res.data;
      setResolvedData(rateData);
    });
  }
};
const checklistBoardTableColumns = ref([
  {
    key: 'check_item',
    title: '检查项',
    align: 'center'
  },
  {
    key: 'baseline',
    title: '基准值',
    align: 'center'
  },
  {
    key: 'operation',
    title: '运算符',
    align: 'center'
  },
  {
    key: 'currentValue',
    title: '现值',
    align: 'center'
  },
  {
    key: 'result',
    title: '检查结果',
    align: 'center',
    render: (row) => {
      if (row.result) {
        return h(
          NIcon,
          {
            color: 'green',
            size: '24',
            style: {
              position: 'relative',
              top: '3px'
            }
          },
          h(CheckCircle, {})
        );
      }
      return h(
        NIcon,
        {
          color: 'rgba(206,64,64,1)',
          size: '26',
          style: {
            position: 'relative',
            top: '1px'
          }
        },
        h(CancelFilled, {})
      );
    }
  }
]);
const active = ref(false); // milestoneIssuesCard弹窗
function handlePackageCardClick() {
  showPackage.value = true;
  packageTabValueFirst.value = 'softwarescope';
  packageTabValueSecond.value = 'everything';
}
function handleListClick() {
  showList.value = true;
}
const activeTab = ref('testProgress'); // 质量看板下方激活模板

// 每日构建弹框
const createDailyBuildRef = ref(null);
const showDailyBuildModal = () => {
  createDailyBuildRef.value.showModal = true;
};
const selectRound = (value) => {
  if (value.id) {
    getBranchSelectList(productId.value);
  }
};
const changePackageTabFirst = (value) => {
  packageTabValueFirst.value = value;
  getPackageCardData(packageTabValueFirst.value);
};

// 切换everything/EPOL
const changePackageTabSecond = (value) => {
  packageTabValueSecond.value = value;
  getPackageCardData(packageTabValueFirst.value);
};
const MilestoneIssuesCardType = computed(() => {
  return resolvedMilestone.value.name === '当前迭代' ? 'round' : 'milestone';
});
export {
  detail,
  productId,
  hasQualityboard,
  tableLoading,
  dashboardId,
  tableData,
  columns,
  productVersionPagination,
  list,
  done,
  currentId,
  roundCompareeId,
  currentRound,
  oldPackage,
  newPackage,
  requestCard,
  boxWidth,
  productList,
  currentProduct,
  currentPanelDetail,
  packageChangeSummary,
  hasMultiVersionPackage,
  showChecklistBoard,
  showRoundMilestoneBoard,
  checklistBoardTablePagination,
  checklistBoardTableLoading,
  checklistBoardTableData,
  additionFeatureSummary,
  inheritFeatureSummary,
  currentResolvedPassed,
  currentResolvedCnt,
  currentResolvedRate,
  currentPanel,
  currentAllCnt,
  defaultMilestoneId,
  seriousMainResolvedPassed,
  seriousResolvedPassed,
  seriousMainResolvedCnt,
  seriousResolvedRate,
  seriousMainResolvedRate,
  seriousMainAllCnt,
  showList,
  showAddNewCompare,
  showPackage,
  leftIssuesCnt,
  leftIssuesPassed,
  issuesResolvedPassed,
  mainResolvedRate,
  mainResolvedPassed,
  resolvedMilestoneOptions,
  resolvedMilestone,
  activeTab,
  active,
  createDailyBuildRef,
  roundId,
  roundIdOptions,
  checklistBoardTableColumns,
  branchOptions,
  branch,
  loadingRef,
  newCompareForm,
  packageCompareClosable,
  productLoading,
  productOptions,
  roundOptions,
  roundLoading,
  packageComparePanels,
  packageTabValueFirst,
  packageTabValueSecond,
  MilestoneIssuesCardType,
  cleanPackageListData,
  exportQualityHistoryFn,
  handleNewCompareCreate,
  handlePackageCompareAdd,
  handlePackageCompareClose,
  getBranchSelectList,
  showDailyBuildModal,
  setResolvedData,
  getFeatureSummary,
  selectResolvedMilestone,
  getPackageListComparationSummary,
  productVersionPageChange,
  productVersionPageSizeChange,
  getVersionTableData,
  getDefaultCheckNode,
  getPackageCardData,
  getRoundRelateMilestones,
  getRoundIssueRate,
  getPackageChangeSummary,
  handleClick,
  haveDone,
  haveRecovery,
  handleRollback,
  selectRound,
  stepAdd,
  handleListClick,
  handlePackageCardClick,
  handleChecklistBoard,
  handleMilestone,
  updateRoundMilestoneBoard,
  checklistBoardTablePageSizeChange,
  checklistBoardTablePageChange,
  changePackageTabFirst,
  changePackageTabSecond,
  getRoundSelectList
};
