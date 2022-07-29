import { ref, h } from 'vue';
import { NButton, NIcon, NSpace, NTag, useMessage } from 'naive-ui';
import { CancelRound, CheckCircleFilled } from '@vicons/material';
import { QuestionCircle16Filled } from '@vicons/fluent';
import { getProduct, getProductMessage, getMilestoneRate } from '@/api/get';
import { createProductMessage } from '@/api/post';
import { milestoneNext } from '@/api/put';
import { detail,drawerShow,showPackage,testProgressList } from './productDetailDrawer';

const ProductId = ref(null);
const done = ref(false);
const dashboardId = ref(null);
const seriousResovledRate = ref(null);
const currentResovledCnt = ref(null);
const currentAllCnt = ref(null);
const currentResovledRate = ref(null);
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
function getDefaultList () {
  testList.value = testProgressList.value[testProgressList.value.length - 1];
}
function getTableData () {
  tableLoading.value = true;
  getProduct().then(res => {
    tableData.value = res.data || [];
    tableLoading.value = false;
  }).catch(() => {
    tableLoading.value = false;
  });
}
function getProductData (id) {
  tableLoading.value = true;
  createProductMessage(id).then(() => {
    tableLoading.value = false;
  }).catch(() => {
    tableLoading.value = false;
  });
}
function getTestList (index) {
  testList.value = testProgressList.value[index];
}

function handleClick(id) {
  currentId.value = id;
  getMilestoneRate(id).then(res => {
    const rateData = res.data;
    for(let i in rateData){
      if(rateData[i] === null){
        rateData[i] = 0;
      }
      if(rateData[i] !== 0 && i.includes('_rate')){
        rateData[i] = rateData[i].toString().substring(0, rateData[i].length - 1);
      }
    }
    seriousResovledRate.value = rateData.serious_resolved_rate;
    currentResovledCnt.value  = rateData.current_resolved_cnt;
    currentAllCnt.value  = rateData.current_all_cnt;
    currentResovledRate.value  = rateData.current_resolved_rate;
    mainResolvedRate.value  = rateData.main_resolved_rate;
    seriousMainResolvedCnt.value  = rateData.serious_main_resolved_cnt;
    seriousMainAllCnt.value  = rateData.serious_main_all_cnt;
    seriousMainResolvedRate.value  = rateData.serious_main_resolved_rate;
    leftIssuesCnt.value = rateData.left_issues_cnt;
    previousLeftResolvedRate.value = rateData.previous_left_resolved_rate ;
  }).catch(() => {
  });
  getTestList(id);
}
function renderBtn (text, action, row, type = 'text') {
  return h(NButton, {
    text: type === 'text',
    onClick: (e) => {
      e.stopPropagation();
      action(row);
    }
  }, text);
}
function releaseclick () {
  currentId.value = null;
}
function editRow () {
  showModal.value = true;
}
function reportRow () {
}
function deleteRow () {
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
    title: '描述',
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
    render (row) {
      if (row.left_resolved_baseline 
        && row.left_resolved_rate
        && row.left_resolved_rate > row.left_resolved_baseline) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false,
          },
          {
            default: `${row.left_resolved_rate}%`,
            icon: () => h(NIcon, {
              component: CheckCircleFilled 
            })
          }
        );
      } else if (!row.left_resolved_rate || !row.left_resolved_baseline) {
        return h(
          NTag,
          {
            type: 'default',
            round: true,
            bordered: false,
          },
          {
            default: 'unknown',
            icon: () => h(NIcon, {
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
          bordered: false,
        },
        {
          default: `${row.left_resolved_rate}%`,
          icon: () => h(NIcon, {
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
    render (row) {
      if (row.serious_main_resolved_baseline 
        && row.serious_main_resolved_rate
        && row.serious_main_resolved_rate > row.serious_main_resolved_baseline) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false,
          },
          {
            default: `${row.serious_main_resolved_rate}%`,
            icon: () => h(NIcon, {
              component: CheckCircleFilled 
            })
          }
        );
      } else if (!row.serious_main_resolved_rate || !row.serious_main_resolved_baseline) {
        return h(
          NTag,
          {
            type: 'default',
            round: true,
            bordered: false,
          },
          {
            default: 'unknown',
            icon: () => h(NIcon, {
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
          bordered: false,
        },
        {
          default: `${row.serious_main_resolved_rate}%`,
          icon: () => h(NIcon, {
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
    render (row) {
      if (row.current_resolved_baseline 
        && row.current_resolved_rate
        && row.current_resolved_rate > row.current_resolved_baseline) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false,
          },
          {
            default: `${row.current_resolved_rate}%`,
            icon: () => h(NIcon, {
              component: CheckCircleFilled 
            })
          }
        );
      } else if (!row.current_resolved_rate || !row.current_resolved_baseline) {
        return h(
          NTag,
          {
            type: 'default',
            round: true,
            bordered: false,
          },
          {
            default: 'unknown',
            icon: () => h(NIcon, {
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
          bordered: false,
        },
        {
          default: `${row.current_resolved_rate}%`,
          icon: () => h(NIcon, {
            component: CancelRound 
          })
        }
      );
    }
  },
  {
    title: '操作',
    align: 'center',
    render (row) {
      return h(NSpace, {
        style: 'justify-content: center'
      }, [
        renderBtn('编辑', editRow, row),
        renderBtn('删除', deleteRow, row),
        renderBtn('报告', reportRow, row),
      ]);
    }
  }
];
function getDefaultCheckNode (id) {
  getProductMessage(id).then(res => {
    dashboardId.value = res.data[0].id;
    const rateData = res.data[0].current_milestone_issue_solved_rate;
    for(let i in rateData){
      if(rateData[i] === null){
        rateData[i] = 0;
      }
      if(rateData[i] !== 0 && i.includes('_rate')){
        rateData[i] = rateData[i].toString().substring(0, rateData[i].length - 1);
      }
    }
    seriousResovledRate.value = rateData.serious_resolved_rate;
    currentResovledCnt.value  = rateData.current_resolved_cnt;
    currentAllCnt.value  = rateData.current_all_cnt;
    currentResovledRate.value  = rateData.current_resolved_rate;
    mainResolvedRate.value  = rateData.main_resolved_rate;
    seriousMainResolvedCnt.value  = rateData.serious_main_resolved_cnt;
    seriousMainAllCnt.value  = rateData.serious_main_all_cnt;
    seriousMainResolvedRate.value  = rateData.serious_main_resolved_rate;
    leftIssuesCnt.value = rateData.left_issues_cnt;
    previousLeftResolvedRate.value = rateData.previous_left_resolved_rate ;
    currentId.value = res.data[0].current_milestone_id;
    const newArr = Object.keys(res.data[0].milestones)
      .map(item => ({key: item, text: res.data[0].milestones[item].name}));
    list.value = newArr;
    tableLoading.value = false;
  }).catch(() => {
    tableLoading.value = false;
  });
}
function rowProps (row) {
  return {
    style:'cursor:pointer',
    onClick: () => {
      detail.value = row;
      drawerShow.value = true;
      list.value = [];
      ProductId.value = row.id;
      getDefaultCheckNode (ProductId.value);
    }
  };
}
function stepAdd() {
  if (list.value.length === 5) {
    window.$message.info('已达到转测最大结点数');
    currentId.value = null;
    done.value = true;
    window.$message.success('已结束迭代测试');
  } else if(list.value.length === 0) {
    createProductMessage(ProductId.value).then(() => {
      window.$message?.info('成功开启第一轮迭代测试');
      getDefaultCheckNode(ProductId.value).then(() => {
        milestoneNext(dashboardId.value).then(res => {
          if (res.error_code === '2000') {
            const newArr = Object.keys(res.data.milestones)
              .map(item => ({key: item, text: res.data.milestones[item].name}));
            list.value = newArr;
            currentId.value = res.data.current_milestone_id;
          } else {
            window.$message.success('节点信息不存在或当前不存在下一轮迭代节点!');
          }
          tableLoading.value = false;
        }).catch(() => {
          tableLoading.value = false;
        });
      });
    });
  } else {
    tableLoading.value = true;
    milestoneNext(dashboardId.value).then(res => {
      if (res.error_code === '2000') {
        const newArr = Object.keys(res.data.milestones)
          .map(item => ({key: item, text: res.data.milestones[item].name}));
        list.value = newArr;
        currentId.value = res.data.current_milestone_id;
      } else {
        window.$message.success('节点信息不存在或当前不存在下一轮迭代节点!');
      }
      tableLoading.value = false;
    }).catch(() => {
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
function haveDone(){
  done.value = true;
  currentId.value = null;
}
function haveRecovery(){
  done.value = false;
  getDefaultCheckNode (ProductId.value);
}
function handlePackageCardClick() {
  showPackage.value = true;
}
export {
  ProductId,
  done,
  testList,
  list,
  currentId,
  dashboardId,
  formRef,
  message,
  model,
  tableData,
  columns,
  tableLoading,
  showModal,
  showCheckList,
  seriousResovledRate,
  currentResovledCnt,
  currentAllCnt,
  currentResovledRate,
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
  releaseclick,
  handlePackageCardClick
};
