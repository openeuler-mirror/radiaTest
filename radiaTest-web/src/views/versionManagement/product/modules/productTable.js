import { ref, h } from 'vue';
import { NButton, NIcon, NSpace, useMessage } from 'naive-ui';
import { CancelRound, CheckCircleFilled } from '@vicons/material';
import { getProduct, getProductMessage, getMilestoneRate } from '@/api/get';
import { createProductMessage } from '@/api/post';
import { milestoneNext } from '@/api/put';
import { detail,drawerShow,testProgressList } from './productDetailDrawer';
const ProductId = ref(null);
const done = ref(false);
const dashboardId = ref(null);
const seriousSovledRate = ref(null);
const currentSovledCnt = ref(null);
const currentAllCnt = ref(null);
const currentSovledRate = ref(null);
const mainSolvedRate = ref(null);
const seriousMainSolvedCnt = ref(null);
const seriousMainAllCnt = ref(null);
const seriousMainSolvedRate = ref(null);
const leftIssuesCnt = ref(null);
const tableData = ref([]);
const testList = ref([]);
const list = ref([]);
const currentId = ref('');
const addmessage = ref('下一轮迭代');
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
  public_time: null,
  bequeath: null,
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
    seriousSovledRate.value = rateData.serious_solved_rate;
    currentSovledCnt.value  = rateData.current_solved_cnt;
    currentAllCnt.value  = rateData.current_all_cnt;
    currentSovledRate.value  = rateData.current_solved_rate;
    mainSolvedRate.value  = rateData.main_solved_rate;
    seriousMainSolvedCnt.value  = rateData.serious_main_solved_cnt;
    seriousMainAllCnt.value  = rateData.serious_main_all_cnt;
    seriousMainSolvedRate.value  = rateData.serious_main_solved_rate;
    leftIssuesCnt.value = rateData.left_issues_cnt;
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
function editRow (row) {
  console.log(row);
  showModal.value = true;
}
function reportRow (row) {
  console.log(row);
}
function deleteRow (row) {
  console.log(row);
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
    key: 'public_time',
    align: 'center',
    title: '发布时间'
  },
  {
    key: 'bequeath',
    align: 'center',
    title: '遗留解决'
  },
  {
    key: 'serious',
    align: 'center',
    title: '严重>80%',
    render () {
      return h(NIcon, { color: 'red',size:24 }, {
        default: () => h(CancelRound)
      });
    }
  },
  {
    key: 'serious',
    align: 'center',
    title: '版本100%',
    render () {
      return h(NIcon, { color: 'green', size: 24 }, {
        default: () => h(CheckCircleFilled)
      });
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
    if(res.data.length === 0){
      getProductData(id);
    }else{
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
      seriousSovledRate.value = rateData.serious_solved_rate;
      currentSovledCnt.value  = rateData.current_solved_cnt;
      currentAllCnt.value  = rateData.current_all_cnt;
      currentSovledRate.value  = rateData.current_solved_rate;
      mainSolvedRate.value  = rateData.main_solved_rate;
      seriousMainSolvedCnt.value  = rateData.serious_main_solved_cnt;
      seriousMainAllCnt.value  = rateData.serious_main_all_cnt;
      seriousMainSolvedRate.value  = rateData.serious_main_solved_rate;
      leftIssuesCnt.value = rateData.left_issues_cnt;
      currentId.value = res.data[0].current_milestone_id;
      const newArr = Object.keys(res.data[0].milestones)
        .map(item => ({key: item, text: res.data[0].milestones[item].name}));
      list.value = newArr;
    }
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
    window.$message.info('已达到转测最大结点数!');
    addmessage.value = '发布';
    currentId.value = null;
    done.value = true;
    window.$message.success('已结束迭代!');
  } else {
    addmessage.value = '下一轮迭代';
    tableLoading.value = true;
    milestoneNext(dashboardId.value).then(res => {
      if (res.error_code === '2000') {
        window.$message.success('迭代成功!');
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
  if(list.value.length === 5){
    addmessage.value = '发布';
  }else{
    addmessage.value = '下一轮迭代';
  }
}
function haveRecovery(){
  done.value = false;
  getDefaultCheckNode (ProductId.value);
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
  addmessage,
  model,
  tableData,
  columns,
  tableLoading,
  showModal,
  showCheckList,
  seriousSovledRate,
  currentSovledCnt,
  currentAllCnt,
  currentSovledRate,
  mainSolvedRate,
  seriousMainSolvedCnt,
  seriousMainAllCnt,
  seriousMainSolvedRate,
  leftIssuesCnt,
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
  releaseclick
};
