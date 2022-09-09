/* eslint-disable no-use-before-define */
/* eslint-disable max-lines-per-function */
import { ref, h } from 'vue';
import { NButton, NIcon, NSpace, NTag, useMessage, NCheckbox } from 'naive-ui';
import { CancelRound, CheckCircleFilled } from '@vicons/material';
import { QuestionCircle16Filled } from '@vicons/fluent';
import { AddAlt } from '@vicons/carbon';
import {
  getProduct,
  getProductMessage,
  getMilestoneRate,
  getCheckListTableRounds,
  getCheckListTableDataAxios
} from '@/api/get';
import { createProductMessage, addCheckListItem } from '@/api/post';
import { milestoneNext, milestoneRollback, updateCheckListItem } from '@/api/put';
import {
  detail,
  drawerShow,
  getFeatureSummary,
  getPackageListComparationSummary,
  showPackage,
  testProgressList
} from './productDetailDrawer';
import _ from 'lodash';

const ProductId = ref(null);
const done = ref(false);
const dashboardId = ref(null);
const seriousResolvedRate = ref(null);
const currentResolvedCnt = ref(null);
const currentAllCnt = ref(null);
const currentResolvedRate = ref(null);
const mainResolvedRate = ref(null);
const seriousMainResolvedCnt = ref(null);
const seriousMainAllCnt = ref(null);
const seriousMainResolvedRate = ref(null);
const leftIssuesCnt = ref(null);
const previousLeftResolvedRate = ref(null);
const tableData = ref([]);
const testList = ref([]);
const list = ref([]);
const currentId = ref('');
const preId = ref('');
const tableLoading = ref(false);
const showModal = ref(false);
const showCheckList = ref(false);
const formRef = ref(null);
const message = useMessage();
const model = ref({
  name: null,
  version: null,
  start_time: null,
  end_time: null,
  publish_time: null,
  previous_left_resolved_rate: null,
  serious_main_resolved_rate: null,
  current_resolved_rate: null
});
const productList = ref([]); // 产品列表
const currentProduct = ref(''); // 当前产品

function getDefaultList() {
  testList.value = testProgressList.value[testProgressList.value.length - 1];
}
function getTableData() {
  tableLoading.value = true;
  getProduct()
    .then((res) => {
      tableData.value = res.data || [];
      tableLoading.value = false;
      productList.value = [];
      res.data?.forEach((v) => {
        productList.value.push({ label: `${v.name} ${v.version}`, value: v.id });
      });
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

function handleClick(id) {
  if (id > currentId.value) {
    dynamicAnimateCss('inout-animated', 'animate__fadeInRight');
  } else {
    dynamicAnimateCss('inout-animated', 'animate__fadeInLeft');
  }
  currentId.value = id;
  getMilestoneRate(id)
    .then((res) => {
      const rateData = res.data;
      for (let i in rateData) {
        if (rateData[i] === null) {
          rateData[i] = 0;
        }
        if (rateData[i] !== 0 && i.includes('_rate')) {
          rateData[i] = rateData[i].toString().substring(0, rateData[i].length - 1);
        }
      }
      seriousResolvedRate.value = rateData.serious_resolved_rate;
      currentResolvedCnt.value = rateData.current_resolved_cnt;
      currentAllCnt.value = rateData.current_all_cnt;
      currentResolvedRate.value = rateData.current_resolved_rate;
      mainResolvedRate.value = rateData.main_resolved_rate;
      seriousMainResolvedCnt.value = rateData.serious_main_resolved_cnt;
      seriousMainAllCnt.value = rateData.serious_main_all_cnt;
      seriousMainResolvedRate.value = rateData.serious_main_resolved_rate;
      leftIssuesCnt.value = rateData.left_issues_cnt;
      previousLeftResolvedRate.value = rateData.previous_left_resolved_rate;
    })
    .catch(() => {});
  getTestList(id);
  getPackageListComparationSummary(dashboardId.value);
}
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
function releaseClick() {
  currentId.value = null;
}
function editRow() {
  showModal.value = true;
}
function reportRow() {}
function deleteRow() {}
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
      if (
        row.left_resolved_baseline !== null &&
        row.left_resolved_rate !== null &&
        row.left_resolved_rate >= row.left_resolved_baseline
      ) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false
          },
          {
            default: `${row.left_resolved_rate}%`,
            icon: () =>
              h(NIcon, {
                component: CheckCircleFilled
              })
          }
        );
      } else if (row.left_resolved_rate === null || row.left_resolved_baseline === null) {
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
          default: `${row.left_resolved_rate}%`,
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
      if (
        row.serious_main_resolved_baseline !== null &&
        row.serious_main_resolved_rate !== null &&
        row.serious_main_resolved_rate >= row.serious_main_resolved_baseline
      ) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false
          },
          {
            default: `${row.serious_main_resolved_rate}%`,
            icon: () =>
              h(NIcon, {
                component: CheckCircleFilled
              })
          }
        );
      } else if (row.serious_main_resolved_rate === null || row.serious_main_resolved_baseline === null) {
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
          default: `${row.serious_main_resolved_rate}%`,
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
      if (
        row.current_resolved_baseline !== null &&
        row.current_resolved_rate !== null &&
        row.current_resolved_rate >= row.current_resolved_baseline
      ) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false
          },
          {
            default: `${row.current_resolved_rate}%`,
            icon: () =>
              h(NIcon, {
                component: CheckCircleFilled
              })
          }
        );
      } else if (row.current_resolved_rate === null || row.current_resolved_baseline === null) {
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
          default: `${row.current_resolved_rate}%`,
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
function getDefaultCheckNode(id) {
  getProductMessage(id)
    .then((res) => {
      dashboardId.value = res.data[0].id;
      const rateData = res.data[0].current_milestone_issue_solved_rate;
      for (let i in rateData) {
        if (rateData[i] === null) {
          rateData[i] = 0;
        }
        if (rateData[i] !== 0 && i.includes('_rate')) {
          rateData[i] = rateData[i].toString().substring(0, rateData[i].length - 1);
        }
      }
      seriousResolvedRate.value = rateData.serious_resolved_rate;
      currentResolvedCnt.value = rateData.current_resolved_cnt;
      currentAllCnt.value = rateData.current_all_cnt;
      currentResolvedRate.value = rateData.current_resolved_rate;
      mainResolvedRate.value = rateData.main_resolved_rate;
      seriousMainResolvedCnt.value = rateData.serious_main_resolved_cnt;
      seriousMainAllCnt.value = rateData.serious_main_all_cnt;
      seriousMainResolvedRate.value = rateData.serious_main_resolved_rate;
      leftIssuesCnt.value = rateData.left_issues_cnt;
      previousLeftResolvedRate.value = rateData.previous_left_resolved_rate;
      currentId.value = res.data[0].current_milestone_id;
      const newArr = Object.keys(res.data[0].milestones).map((item) => ({
        key: item,
        text: res.data[0].milestones[item].name
      }));
      list.value = newArr;
      tableLoading.value = false;
      getFeatureSummary(dashboardId.value);
      getPackageListComparationSummary(dashboardId.value);
    })
    .catch(() => {
      tableLoading.value = false;
    });
}
function rowProps(row) {
  return {
    style: 'cursor:pointer',
    onClick: () => {
      detail.value = row;
      drawerShow.value = true;
      list.value = [];
      ProductId.value = row.id;
      getDefaultCheckNode(ProductId.value);
    }
  };
}

function haveDone() {
  tableLoading.value = true;
  milestoneNext(dashboardId.value, { released: true })
    .then((res) => {
      if (res.error_code === '2000') {
        const newArr = Object.keys(res.data.milestones).map((item) => ({
          key: item,
          text: res.data.milestones[item].name
        }));
        list.value = newArr;
        currentId.value = res.data.current_milestone_id;
        done.value = true;
        window.$message.error('已正式发布');
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

function stepAdd() {
  if (list.value.length === 5) {
    window.$message.info('已达到转测最大结点数');
    haveDone();
  } else if (list.value.length === 0) {
    createProductMessage(ProductId.value)
      .then(() => {
        window.$message?.info('第一轮迭代已转测');
        getDefaultCheckNode(ProductId.value);
      })
      .catch(() => {
        window.$message?.info('第一轮迭代转测失败');
      })
      .finally(() => {
        tableLoading.value = false;
      });
  } else {
    tableLoading.value = true;
    milestoneNext(dashboardId.value)
      .then((res) => {
        if (res.error_code === '2000') {
          const newArr = Object.keys(res.data.milestones).map((item) => ({
            key: item,
            text: res.data.milestones[item].name
          }));
          list.value = newArr;
          currentId.value = res.data.current_milestone_id;
          window.$message.success('下一轮迭代已转测');
        } else {
          window.$message.error('下一轮迭代转测失败');
        }
        getDefaultCheckNode(ProductId.value);
      })
      .catch(() => {
        window.$message.error('下一轮迭代转测失败');
      })
      .finally(() => {
        tableLoading.value = false;
      });
  }
}
function handleValidateButtonClick(e) {
  e.preventDefault();
  formRef.value?.validate((errors) => {
    if (!errors) {
      window.$message.success('修改信息成功');
      setTimeout(() => {
        showModal.value = false;
      }, 200);
    } else {
      window.$message.success('修改信息失败');
    }
  });
}
function handleRollback() {
  milestoneRollback(dashboardId.value)
    .then(() => {
      getDefaultCheckNode(ProductId.value);
      window.$message?.success('当前进展已回退至上一轮迭代');
    })
    .catch(() => {
      window.$message?.error('回退失败');
    });
}
function haveRecovery() {
  handleRollback().then(() => {
    done.value = false;
  });
}
function handlePackageCardClick() {
  showPackage.value = true;
}

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

const rounds = ref({}); // checkList表格Rounds数
const checkListTableColumns = ref([]);

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
    key: 'lts',
    title: 'lts',
    align: 'center',
    render: (row) => {
      return h(NCheckbox, {
        focusable: false,
        checked: row.lts ? true : false,
        'on-update:checked': (checked) => {
          updateCheckListTable(row, { lts: checked });
        }
      });
    }
  },
  {
    key: 'lts_spx',
    title: 'lts_spx',
    align: 'center',
    render: (row) => {
      return h(NCheckbox, {
        focusable: false,
        checked: row.lts_spx ? true : false,
        'on-update:checked': (checked) => {
          updateCheckListTable(row, { lts_spx: checked });
        }
      });
    }
  },
  {
    key: 'innovation',
    title: 'innovation',
    align: 'center',
    render: (row) => {
      return h(NCheckbox, {
        focusable: false,
        checked: row.innovation ? true : false,
        'on-update:checked': (checked) => {
          updateCheckListTable(row, { innovation: checked });
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
          bordered: false,
          'on-click': () => {
            let keyName = `R${rounds.value + 1}`;
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
  }
];

const showCheckListDrawer = ref(false);
const checkListDrawerFormRef = ref(null);

const checkListDrawerModel = ref({
  product_id: null,
  check_item: null,
  baseline: null,
  operation: null
});

const checkListDrawerRules = ref({
  check_item: {
    required: true,
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
  getCheckListTableDataAxios({ page_num: currentPage, page_size: pageSize, product_id: productId }).then((res) => {
    checkListTableLoading.value = false;
    checkListTableData.value = [];
    res.data.items?.forEach((item) => {
      checkListTableData.value.push({
        id: item.id,
        check_item: item.check_item,
        baseline: item.baseline,
        operation: item.operation,
        lts: item.lts,
        lts_spx: item.lts_spx,
        innovation: item.innovation,
        rounds: item.rounds
      });
    });
    checkListTablePagination.value.page = currentPage;
    checkListTablePagination.value.pageSize = pageSize;
    checkListTablePagination.value.pageCount = res.data.pages;
  });
};

// 更新checkList表格检查项状态
const updateCheckListTable = (row, data) => {
  let [key] = Object.keys(data);
  if (data.rounds) {
    data.rounds = data.rounds.replace(/(0+)\b/gi, '');
  }
  updateCheckListItem(row.id, data).then(() => {
    row[key] = data[key];
  });
};

const checkListTablePageChange = (page) => {
  getCheckListTableData(page, checkListTablePagination.value.pageSize, currentProduct.value);
};

const checkListTablePageSizeChange = (pageSize) => {
  getCheckListTableData(1, pageSize, currentProduct.value);
};

// 点击质量checklist按钮
const clickCheckList = async () => {
  showCheckList.value = true;
  checkListTableColumns.value = _.cloneDeep(checkListTableColumnsDefault);
  rounds.value = (await getCheckListTableRounds(currentProduct.value)).count;
  for (let i = 0; i < rounds.value; i++) {
    let keyName = `R${i + 1}`;
    addRounds(i, keyName);
  }
  await getCheckListTableData(1, checkListTablePagination.value.pageSize, currentProduct.value);
};

// 添加checklist表格rounds列
const addRounds = (index, keyName) => {
  checkListTableColumns.value.splice(index + 6, 0, {
    key: keyName,
    title: keyName,
    align: 'center',
    render: (row) => {
      if (row.rounds.length < rounds.value) {
        row.rounds = `${row.rounds}0`;
      }
      return h(NCheckbox, {
        focusable: false,
        checked: Number(row.rounds[index]) ? true : false,
        'on-update:checked': (checked) => {
          let tempArr = row.rounds.split('');
          checked ? (tempArr[index] = 1) : (tempArr[index] = 0);
          row.rounds = tempArr.join('');
          updateCheckListTable(row, { rounds: row.rounds });
        }
      });
    }
  });
};

const cancelCheckListDrawer = () => {
  showCheckListDrawer.value = false;
  checkListDrawerModel.value = {
    product_id: null,
    check_item: null,
    baseline: null,
    operation: null
  };
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

// 点击新增检查项按钮
const addCheckItem = () => {
  showCheckListDrawer.value = true;
  checkListDrawerModel.value.product_id = currentProduct.value;
};

export {
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
  formRef,
  message,
  model,
  tableData,
  columns,
  tableLoading,
  showModal,
  showCheckList,
  seriousResolvedRate,
  currentResolvedCnt,
  currentAllCnt,
  currentResolvedRate,
  mainResolvedRate,
  seriousMainResolvedCnt,
  seriousMainAllCnt,
  seriousMainResolvedRate,
  leftIssuesCnt,
  previousLeftResolvedRate,
  stepAdd,
  getTestList,
  handleClick,
  getDefaultList,
  handleValidateButtonClick,
  rowProps,
  getTableData,
  getProductData,
  haveDone,
  haveRecovery,
  getDefaultCheckNode,
  releaseClick,
  handlePackageCardClick,
  handleRollback
};
