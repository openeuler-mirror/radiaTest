/* eslint-disable no-use-before-define */
/* eslint-disable max-lines-per-function */
import { NButton, NIcon, NSpace, NTag, useMessage, NCheckbox } from 'naive-ui';
import { CancelRound, CheckCircleFilled } from '@vicons/material';
import { QuestionCircle16Filled } from '@vicons/fluent';
import { AddAlt } from '@vicons/carbon';
import {
  getProduct,
  getProductMessage,
  getMilestoneRate,
  getCheckListTableRounds,
  getCheckListTableDataAxios,
  getMilestones,
  getRoundIssueRate
} from '@/api/get';
import { createProductMessage, addCheckListItem } from '@/api/post';
import {
  milestoneNext,
  milestoneRollback,
  updateCheckListItem,
  deselectCheckListItem,
  updateProductVersion
} from '@/api/put';
import { deleteCheckListItem, deleteProductVersion } from '@/api/delete';
import {
  detail,
  drawerShow,
  getFeatureSummary,
  getPackageListComparationSummary,
  showPackage,
  testProgressList
} from './productDetailDrawer';
import _ from 'lodash';
import textDialog from '@/assets/utils/dialog';
import { CheckmarkCircle, CloseCircleOutline } from '@vicons/ionicons5';
import { getCheckItemOpts } from '@/assets/utils/getOpts';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';

const ProductId = ref(null);
const done = ref(false);
const dashboardId = ref(null);

const seriousResolvedRate = ref(null);
const seriousResolvedPassed = ref(null);
const mainResolvedRate = ref(null);
const mainResolvedPassed = ref(null);
const seriousMainResolvedCnt = ref(null);
const seriousMainAllCnt = ref(null);
const seriousMainResolvedRate = ref(null);
const seriousMainResolvedPassed = ref(null);

const currentResolvedCnt = ref(null);
const currentAllCnt = ref(null);
const currentResolvedRate = ref(null);
const currentResolvedPassed = ref(null);

const leftIssuesCnt = ref(null);
const leftIssuesPassed = ref(null);
const previousLeftResolvedRate = ref(null);
const previousLeftResolvedPassed = ref(null);
const issuesResolvedPassed = ref(null);
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

const tableData = ref([]);
const testList = ref([]);
const list = ref([]);
const currentId = ref('');
const preId = ref('');
const tableLoading = ref(false);
const showCheckList = ref(false);
const message = useMessage();
const productList = ref([]); // 产品列表
const currentProduct = ref(''); // 当前产品
const checkItemList = ref([]); // 检查项列表
const existedCheckItemList = ref([]); // 新增基准值表单检查项列表

function getDefaultList() {
  testList.value = testProgressList.value[testProgressList.value.length - 1];
}
function getTableData() {
  tableLoading.value = true;
  getProduct()
    .then((res) => {
      tableData.value = res.data || [];
      tableLoading.value = false;
    })
    .catch(() => {
      tableLoading.value = false;
    });
}
function getProductData(id) {
  tableLoading.value = true;
  createProductMessage(id)
    .then(() => {
      tableLoading.value = false;
    })
    .catch(() => {
      tableLoading.value = false;
    });
}
function getTestList(index) {
  testList.value = testProgressList.value[index];
}

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

const currentRound = ref({});
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
  previousLeftResolvedRate.value = rateData.previous_left_resolved_rate;
  previousLeftResolvedPassed.value = rateData.previous_left_resolved_passed;
};

// 点击每个Round
function handleClick(item) {
  currentRound.value = item;
  if (item.id > currentId.value) {
    dynamicAnimateCss('inout-animated', 'animate__fadeInRight');
  } else {
    dynamicAnimateCss('inout-animated', 'animate__fadeInLeft');
  }
  currentId.value = item.id;
  getRoundRelateMilestones(item.id);
  getRoundIssueRate(item.id)
    .then((res) => {
      const rateData = res.data;
      setResolvedData(rateData);
    })
    .catch(() => {});
  getTestList(item.id);
  getPackageCardData(packageTabValueFirst.value);
}

const showEditProductVersionModal = ref(false);
const productVersionFormRef = ref(null);
const productVersionModel = ref({
  name: null,
  version: null,
  description: null,
  start_time: null,
  end_time: null
});
const editProductId = ref(null);

function editRow(row) {
  editProductId.value = row.id;
  showEditProductVersionModal.value = true;
}

const cancelEditProductVersionModal = () => {
  showEditProductVersionModal.value = false;
  productVersionModel.value = {
    name: null,
    version: null,
    description: null,
    start_time: null,
    end_time: null
  };
};

function confirmEditProductVersionModal(e) {
  e.preventDefault();
  productVersionFormRef.value?.validate((errors) => {
    if (!errors) {
      let obj = { ...productVersionModel.value };
      obj.start_time = obj.start_time ? formatTime(obj.start_time, 'yyyy-MM-dd hh:mm:ss') : null;
      obj.end_time = obj.end_time ? formatTime(obj.end_time, 'yyyy-MM-dd hh:mm:ss') : null;

      updateProductVersion(editProductId.value, obj).then(() => {
        cancelEditProductVersionModal();
        getTableData();
      });
    }
  });
}

function deleteRow(row) {
  textDialog('warning', '警告', '确认删除产品版本？', () => {
    deleteProductVersion(row.id).then(() => {
      getTableData();
    });
  });
}

function reportRow() {}

function renderBtn(text, action, row, type = 'text') {
  return h(
    NButton,
    {
      text: type === 'text',
      onClick: (e) => {
        e.stopPropagation();
        action(row);
      }
    },
    text
  );
}

const columns = [
  {
    key: 'name',
    title: '产品',
    align: 'center'
  },
  {
    key: 'version',
    align: 'center',
    title: '版本'
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
    key: 'previous_left_resolved_rate',
    align: 'center',
    className: 'resolvedRate',
    title: '遗留问题解决率',
    render(row) {
      if (row.left_resolved_passed === true) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false
          },
          {
            default: row.left_resolved_rate,
            icon: () =>
              h(NIcon, {
                component: CheckCircleFilled
              })
          }
        );
      } else if (row.left_resolved_passed !== false) {
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
          default: row.left_resolved_rate,
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
    title: '操作',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          style: 'justify-content: center'
        },
        [renderBtn('编辑', editRow, row), renderBtn('删除', deleteRow, row), renderBtn('报告', reportRow, row)]
      );
    }
  }
];

const hasQualityboard = ref(false);

// 获取qualityboard数据
function getDefaultCheckNode(id) {
  getProductMessage(id)
    .then((res) => {
      dashboardId.value = res.data[0].id;
      hasQualityboard.value = true;
      const rateData = res.data[0].current_round_issue_solved_rate;
      setResolvedData(rateData);
      currentId.value = res.data[0].current_round_id;
      const newArr = Object.keys(res.data[0].rounds).map((item) => {
        if (item === currentId.value) {
          currentRound.value = res.data[0].rounds[item];
        }
        return {
          id: item,
          name: res.data[0].rounds[item].name,
          type: res.data[0].rounds[item].type,
          product_id: res.data[0].rounds[item].product_id
        };
      });
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

// 点击某产品版本
function rowProps(row) {
  return {
    style: 'cursor:pointer',
    onClick: () => {
      detail.value = row;
      drawerShow.value = true;
      list.value = [];
      hasQualityboard.value = false;
      ProductId.value = row.id;
      getDefaultCheckNode(ProductId.value);
    }
  };
}

// 发布
function haveDone() {
  tableLoading.value = true;
  milestoneNext(dashboardId.value, { released: true })
    .then((res) => {
      if (res.error_code === '2000') {
        const newArr = Object.keys(res.data.rounds).map((item) => ({
          id: item,
          name: res.data.rounds[item].name,
          type: res.data.rounds[item].type,
          product_id: res.data.rounds[item].product_id
        }));
        list.value = newArr;
        currentId.value = res.data.current_round_id;
        done.value = true;
        window.$message.success('已正式发布');
      } else {
        window.$message.error('发布失败');
      }
      tableLoading.value = false;
      getDefaultCheckNode(ProductId.value);
    })
    .catch(() => {
      window.$message.error('发布失败');
      done.value = false;
      tableLoading.value = false;
    });
}

// 点击转测图标
function stepAdd() {
  if (hasQualityboard.value === false) {
    createProductMessage(ProductId.value)
      .then(() => {
        window.$message?.info('已创建qualityboard');
        getDefaultCheckNode(ProductId.value);
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
          const newArr = Object.keys(res.data.rounds).map((item) => ({
            id: item,
            name: res.data.rounds[item].name,
            type: res.data.rounds[item].type,
            product_id: res.data.rounds[item].product_id
          }));
          list.value = newArr;
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

// 回退
function handleRollback(recovery = false) {
  milestoneRollback(dashboardId.value)
    .then(() => {
      getDefaultCheckNode(ProductId.value);
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

// 回退至最后一轮迭代
function haveRecovery() {
  handleRollback(true);
}

const resolvedMilestone = ref({});
const resolvedMilestoneOptions = ref([]);

const getRoundRelateMilestones = (roundId) => {
  resolvedMilestoneOptions.value = [
    { label: currentRound.value.name, value: { name: '当前迭代', id: currentRound.value.id } }
  ];
  getMilestones({ round_id: roundId, paged: false }).then((res) => {
    res.data.items.forEach((item) => {
      resolvedMilestoneOptions.value.push({
        label: item.name,
        value: { name: item.name, id: item.id }
      });
    });
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

const packageTabValueFirst = ref('softwarescope');
const packageTabValueSecond = ref('everything');

// 点击软件包变更卡片
function handlePackageCardClick() {
  showPackage.value = true;
  packageTabValueFirst.value = 'softwarescope';
  packageTabValueSecond.value = 'everything';
}

const getPackageCardData = (type) => {
  if (type === 'softwarescope') {
    getPackageListComparationSummary(dashboardId.value, {
      refresh: false,
      repoPath: packageTabValueSecond.value,
      arch: 'all'
    });
  }
};

// 切换软件包变更tab第一层
const changePackageTabFirst = (value) => {
  packageTabValueFirst.value = value;
  getPackageCardData(packageTabValueFirst.value);
};

// 切换软件包变更tab第二层
const changePackageTabSecond = (value) => {
  packageTabValueSecond.value = value;
  getPackageCardData(packageTabValueFirst.value);
};

const searchInfo = ref('');
const checkListTableLoading = ref(false);
const checkListTablePagination = ref({
  page: 1,
  pageSize: 10, //受控模式下的分页大小
  pageCount: 1, //总页数
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});

const checkListTableData = ref([]);

const rounds = ref(1); // checkList表格Rounds数
const checkListTableColumns = ref([]);

const deleteCheckItem = (row) => {
  deleteCheckListItem(row.id).then(() => {
    getCheckListTableData(1, checkListTablePagination.value.pageSize, currentProduct.value);
  });
};

const checkListTableColumnsDefault = [
  {
    key: 'check_item',
    title: '检查项',
    align: 'center'
  },
  {
    key: 'baseline',
    title: '基准',
    align: 'center'
  },
  {
    key: 'operation',
    title: '运算符',
    align: 'center'
  },
  {
    key: 'released',
    title: 'released',
    align: 'center',
    render: (row) => {
      return h(NCheckbox, {
        focusable: false,
        checked: Number(row.rounds[0]) ? true : false,
        'on-update:checked': (checked) => {
          let tempArr = row.rounds.split('');
          checked ? (tempArr[0] = 1) : (tempArr[0] = 0);
          row.rounds = tempArr.join('');
          if (checked) {
            updateCheckListTable(row, {
              baseline: row.baseline,
              operation: row.operation,
              rounds: '1'
            });
          } else {
            deselectCheckListItem(row.id, { rounds: '1' });
          }
        }
      });
    }
  },
  {
    key: 'addCol',
    align: 'center',
    title() {
      return h(
        NButton,
        {
          title: '新增产品Rounds',
          bordered: false,
          'on-click': () => {
            let keyName = `R${rounds.value}`;
            addRounds(rounds.value, keyName);
            rounds.value = rounds.value + 1;
          }
        },
        {
          default: () => {
            return h(NIcon, {
              component: AddAlt
            });
          }
        }
      );
    }
  },
  {
    title: '操作',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          style: 'justify-content: center'
        },
        [
          h(
            NButton,
            {
              text: true,
              onClick: () => {
                textDialog('warning', '警告', '确认删除检查项？', () => {
                  deleteCheckItem(row);
                });
              }
            },
            '删除'
          )
        ]
      );
    }
  }
];

const showCheckListDrawer = ref(false);
const checkListDrawerFormRef = ref(null);
const isAddBaseline = ref(false);
const roundsOptions = ref([]);

const checkListDrawerModel = ref({
  product_id: null,
  checkitem_id: null,
  baseline: null,
  operation: null
});

const checkListDrawerRules = ref({
  checkitem_id: {
    required: true,
    type: 'number',
    message: '检查项必填',
    trigger: ['blur', 'input']
  },
  baseline: {
    required: true,
    message: '基准数值必填',
    trigger: ['blur', 'input']
  },
  operation: {
    required: true,
    message: '请选择运算符',
    trigger: ['blur', 'change']
  },
  rounds: {
    required: true,
    message: '请选择迭代版本',
    trigger: ['blur', 'change']
  }
});

const operationOptions = ref([
  {
    label: '>',
    value: '>'
  },
  {
    label: '<',
    value: '<'
  },
  {
    label: '=',
    value: '='
  },
  {
    label: '>=',
    value: '>='
  },
  {
    label: '<=',
    value: '<='
  }
]);

const onlyAllowNumber = (value) => !value || /^-?\d*\.?\d{0,2}%?$/.test(value);

const getCheckListTableData = (currentPage, pageSize, productId) => {
  checkListTableLoading.value = true;
  getCheckListTableDataAxios({ page_num: currentPage, page_size: pageSize, product_id: productId, paged: false }).then(
    (res) => {
      checkListTableLoading.value = false;
      checkListTableData.value = [];
      existedCheckItemList.value = [];
      res.data.items?.forEach((item) => {
        checkListTableData.value.push({
          id: item.id,
          check_item: item.check_item,
          baseline: item.baseline,
          operation: item.operation,
          released: item.released,
          rounds: item.rounds
        });

        let isExisted = false;
        existedCheckItemList.value.forEach((item2) => {
          if (item.check_item === item2.label) {
            isExisted = true;
          }
        });
        if (!isExisted) {
          existedCheckItemList.value.push({ label: item.check_item, value: item.id });
        }
      });
      checkListTablePagination.value.page = currentPage;
      checkListTablePagination.value.pageSize = pageSize;
      checkListTablePagination.value.pageCount = res.data.pages;
    }
  );
};

// 更新checkList表格检查项状态
const updateCheckListTable = (row, data) => {
  updateCheckListItem(row.id, data).then(() => {
    getCheckListTableData(
      checkListTablePagination.value.page,
      checkListTablePagination.value.pageSize,
      currentProduct.value
    );
  });
};

const checkListTablePageChange = (page) => {
  checkListTablePagination.value.page = page;
};

const checkListTablePageSizeChange = (pageSize) => {
  checkListTablePagination.value.page = 1;
  checkListTablePagination.value.pageSize = pageSize;
};

const checkListModalTitle = ref('');

// 点击质量checklist按钮
const clickCheckList = async () => {
  productList.value.forEach((item) => {
    if (item.value === currentProduct.value) {
      checkListModalTitle.value = `${item.label} checkList信息`;
    }
  });
  showCheckList.value = true;
  checkListTableColumns.value = _.cloneDeep(checkListTableColumnsDefault);
  rounds.value = (await getCheckListTableRounds({ product_id: currentProduct.value })).count || 1;
  for (let i = 1; i <= rounds.value - 1; i++) {
    let keyName = `R${i}`;
    addRounds(i, keyName);
  }
  await getCheckListTableData(1, checkListTablePagination.value.pageSize, currentProduct.value);
};

const createRoundNumber = (num) => {
  let tempArr = [];
  for (let i = 0; i <= num; i++) {
    tempArr[i] = 0;
  }
  tempArr[num] = 1;
  return tempArr.join('');
};

// 添加checklist表格rounds列
const addRounds = (index, keyName) => {
  checkListTableColumns.value.splice(index + 3, 0, {
    key: keyName,
    title: keyName,
    align: 'center',
    render: (row) => {
      if (row.rounds.length < rounds.value) {
        row.rounds = row.rounds.padEnd(rounds.value, '0');
      }
      return h(NCheckbox, {
        focusable: false,
        checked: Number(row.rounds[index]) ? true : false,
        'on-update:checked': (checked) => {
          let tempArr = row.rounds.split('');
          checked ? (tempArr[index] = 1) : (tempArr[index] = 0);
          row.rounds = tempArr.join('');
          if (checked) {
            updateCheckListTable(row, {
              rounds: createRoundNumber(index),
              baseline: row.baseline,
              operation: row.operation
            });
          } else {
            deselectCheckListItem(row.id, { rounds: createRoundNumber(index) });
          }
        }
      });
    }
  });
};

const cancelCheckListDrawer = () => {
  showCheckListDrawer.value = false;
  checkListDrawerModel.value = {};
};

// 确认新增检查项
const confirmCheckItem = () => {
  checkListDrawerFormRef.value?.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      addCheckListItem(checkListDrawerModel.value).then(() => {
        getCheckListTableData(1, checkListTablePagination.value.pageSize, currentProduct.value);
        cancelCheckListDrawer();
      });
    }
  });
};

// 确认新增基准值
const confirmBaseline = () => {
  checkListDrawerFormRef.value?.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      updateCheckListItem(checkListDrawerModel.value.checkitem_id, {
        baseline: checkListDrawerModel.value.baseline,
        operation: checkListDrawerModel.value.operation,
        rounds: checkListDrawerModel.value.rounds
      }).then(() => {
        getCheckListTableData(1, checkListTablePagination.value.pageSize, currentProduct.value);
        cancelCheckListDrawer();
      });
    }
  });
};

const createRoundsOptions = (num) => {
  let tempArr = [{ label: 'released', value: '1' }];
  for (let i = 1; i < num; i++) {
    tempArr.push({
      label: `R${i}`,
      value: createRoundNumber(i)
    });
  }
  return tempArr;
};

// 点击新增检查项按钮
const addCheckItem = () => {
  getCheckItemOpts(checkItemList);
  showCheckListDrawer.value = true;
  isAddBaseline.value = false;
  checkListDrawerModel.value.product_id = currentProduct.value;
};

// 点击新增基准值按钮
const addBaseline = async () => {
  isAddBaseline.value = true;
  roundsOptions.value = createRoundsOptions(rounds.value);
  checkListDrawerModel.value.product_id = currentProduct.value;
  showCheckListDrawer.value = true;
};

const showChecklistBoard = ref(false);
const checklistBoardTableLoading = ref(false);
const checklistBoardTableData = ref([]);

const checklistBoardTablePagination = ref({
  page: 1,
  pageSize: 3, //受控模式下的分页大小
  pageCount: 1, //总页数
  showSizePicker: true,
  pageSizes: [1, 3, 5, 10]
  // pageSizes: [5, 10, 20, 50]
});
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
      return h(
        NTag,
        {
          type: row.result ? 'success' : 'error'
        },
        {
          icon: () => h(NIcon, { component: row.result ? CheckmarkCircle : CloseCircleOutline }),
          default: () => (row.result ? '检查通过' : '检查未通过')
        }
      );
    }
  }
]);

// 点击round的checklist图标
const handleChecklistBoard = () => {
  showChecklistBoard.value = true;
};

const checklistBoardTablePageChange = (page) => {
  checklistBoardTablePagination.value.page = page;
};

const checklistBoardTablePageSizeChange = (pageSize) => {
  checklistBoardTablePagination.value.page = 1;
  checklistBoardTablePagination.value.pageSize = pageSize;
};

const showRoundMilestoneBoard = ref(false);
const handleMilestone = () => {
  showRoundMilestoneBoard.value = true;
};

const updateRoundMilestoneBoard = (value) => {
  if (!value) {
    getRoundRelateMilestones(currentRound.value.id);
  }
};

export {
  packageTabValueFirst,
  packageTabValueSecond,
  changePackageTabFirst,
  changePackageTabSecond,
  selectResolvedMilestone,
  updateRoundMilestoneBoard,
  resolvedMilestone,
  resolvedMilestoneOptions,
  currentRound,
  handleMilestone,
  showRoundMilestoneBoard,
  checkListModalTitle,
  roundsOptions,
  existedCheckItemList,
  confirmBaseline,
  isAddBaseline,
  addBaseline,
  checklistBoardTablePageSizeChange,
  checklistBoardTablePageChange,
  checklistBoardTablePagination,
  checklistBoardTableData,
  checklistBoardTableColumns,
  checklistBoardTableLoading,
  showChecklistBoard,
  handleChecklistBoard,
  checkListTablePageChange,
  checkListTablePageSizeChange,
  checkListTablePagination,
  onlyAllowNumber,
  checkListDrawerFormRef,
  cancelCheckListDrawer,
  confirmCheckItem,
  operationOptions,
  checkListDrawerRules,
  checkListDrawerModel,
  showCheckListDrawer,
  addCheckItem,
  rounds,
  checkListTableColumns,
  checkListTableData,
  checkListTableLoading,
  clickCheckList,
  productList,
  currentProduct,
  searchInfo,
  ProductId,
  done,
  testList,
  list,
  currentId,
  preId,
  dashboardId,
  productVersionFormRef,
  message,
  productVersionModel,
  tableData,
  columns,
  tableLoading,
  showEditProductVersionModal,
  showCheckList,
  seriousMainResolvedCnt,
  seriousMainAllCnt,
  seriousResolvedRate,
  seriousResolvedPassed,
  mainResolvedPassed,
  mainResolvedRate,
  seriousMainResolvedRate,
  seriousMainResolvedPassed,
  currentResolvedCnt,
  currentAllCnt,
  currentResolvedRate,
  currentResolvedPassed,
  leftIssuesCnt,
  leftIssuesPassed,
  previousLeftResolvedRate,
  previousLeftResolvedPassed,
  issuesResolvedPassed,
  checkItemList,
  stepAdd,
  getTestList,
  handleClick,
  getDefaultList,
  confirmEditProductVersionModal,
  rowProps,
  getTableData,
  getProductData,
  haveDone,
  haveRecovery,
  getDefaultCheckNode,
  handlePackageCardClick,
  handleRollback,
  cancelEditProductVersionModal,
  hasQualityboard
};
