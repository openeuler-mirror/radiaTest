import { ref } from 'vue';
import router from '@/router';
import { getBaselineTask } from '@/api/get';
const task = ref({});
function getTask () {
  const baselineId = window.atob(router.currentRoute.value.params.directoryId);
  getBaselineTask(baselineId).then(res => {
    task.value = res.data;
  });
}
export {
  task,
  getTask
};
