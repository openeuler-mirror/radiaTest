import { ref } from 'vue';
import router from '@/router';
import { getCaseNodeTask } from '@/api/get';
const task = ref({});
function getTask () {
  const caseNodeId = window.atob(router.currentRoute.value.params.directoryId);
  getCaseNodeTask(caseNodeId).then(res => {
    task.value = res.data;
  });
}
export {
  task,
  getTask
};
