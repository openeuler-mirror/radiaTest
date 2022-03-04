import axios from '@/axios';
import { ref } from 'vue';
import { caseInfo } from './details';
const createForm = ref();
function showCreateForm () {
  createForm.value.open();
}
function createRelationTask (form) {
  const formData = { ...form, status_id: 1, is_single_case: true, case_id: caseInfo.value.id, is_version_task: form.type === 'VERSION' };
  axios.post('/v1/tasks', formData).then(() => {
    window.$message?.success('任务创建成功');
  }).catch(err => window.$message?.error(err.data.error_msg || '未知错误'));
  console.log(formData);
}
export {
  createForm,
  showCreateForm,
  createRelationTask
};
