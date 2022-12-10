import { ref } from 'vue';
import actions from '@/assets/CRUD/update/updateAjax';
import {getTimeline,records,caseDetail} from './line';
import logMethod from '@/views/testCenter/job/modules/logsDrawer';
const selectedRecord = ref();
const selectedStage = ref('');
const logsData = ref('');
function newIssueRedirect(url){
  logMethod.handleNewIssueRedirect(url);
}
function updateSelectRecord(recordId){
  getTimeline(caseDetail).then(()=>{
    selectedRecord.value = records.value.find(item=>item.id=== recordId);
  }).catch(err=>window.$message?.error(err.data.error_msg||'未知错误'));
}
function emitUpdateEvent(){
  actions.handleSuccessUpdate();
  updateSelectRecord(selectedRecord.value.id);
}
export {
  selectedRecord,
  logsData,
  selectedStage,
  newIssueRedirect,
  emitUpdateEvent
};
