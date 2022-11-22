import { ref } from 'vue';
import router from '@/router';
const testStrategyProgress = [
  {
    label: '',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 80
  }
];

const baseline = ref('LTS版本基线-220609');

function openReport() {}
function createVersionTask() {
  const { href } = router.resolve({
    path: '/home/tm/task',
    query: {
      type: 'caseManage'
    }
  });
  window.open(href, '_blank');
}

function initData() {
  //
}
export {
  testStrategyProgress,
  baseline,
  openReport,
  createVersionTask,
  initData
};
