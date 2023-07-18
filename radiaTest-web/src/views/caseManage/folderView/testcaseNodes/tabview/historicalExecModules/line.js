import {ref} from 'vue';
import axios from '@/axios';
import {logsData,selectedRecord} from './details';
const records = ref();
let cloneRecords;
let caseDetail;
const getAnalysisList = (_case,record) => {
  return [
    {
      title: '用例信息', name: 'caseInfo', rows: [
        { cols: [{ label: '用例名', value: _case.name }] },
        { cols: [{label:'用例描述',value: _case.description }] },
      ]
    },
    {
      title: '分析记录', name: 'analysisRecord', rows: [
        { cols: [{ label: '问题类型', value: record.fail_type }] },
        { cols: [{ label: '问题描述', value: record.details, type: 'pre' }] },
        { cols: [{ label: 'issue地址', value: record.issue_url, type: 'html' }] },
        { cols: [{ label: '日志地址', value: record.log_url, type: 'html' }] },
      ],
    },
  ];
};
function handleline(value){
  axios.get(`/v1/analyzed/${value.id}/logs`
  ).then(res=>{
    logsData.value = res.data;
    selectedRecord.value = value;
  });
}
function timeChange(time){
  selectedRecord.value = '';
  const [startTime,endTime] = time;
  if(startTime>0||endTime>0){
    records.value = cloneRecords.filter(item=>(new Date(item.create_time).getTime()>=startTime&& new Date(item.create_time).getTime()<=endTime));
  }else{
    records.value = cloneRecords.map(item=>item);
  }
}
function checkdChange(checked){
  selectedRecord.value = '';
  records.value = cloneRecords.filter(item=>{
    if(checked.records){
      return item.result === 'fail';
    } 
    return item.result === 'success';
  });
  if(checked.milestone){
    records.value = records.value.filter(item=>item.milestone_id === checked.milestone);
  }
}
function getTimeline(caseInfo){
  caseDetail = caseInfo;
  return new Promise((resolve,reject)=>{
    axios.get('/v1/analyzed/records',{
      case_id:caseInfo.id
    }).then(res=>{
      records.value = res.data.map(item=>item);
      cloneRecords = res.data.map(item=>item);
      resolve();
    }).catch(err=>reject(err));
  });
}
export {
  caseDetail,
  records,
  handleline,
  timeChange,
  getTimeline,
  checkdChange,
  getAnalysisList,
};
