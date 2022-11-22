import { ref } from 'vue';
import router from '@/router';

const testCaseProgress = [
  {
    label: '',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 80
  }
];

const activeTab = ref('details');

function openReport () {
  //
}

function goTaskPage () {
  const { href } = router.resolve({
    path: '/home/tm/task',
    query: {
      type: 'caseManage'
    }
  });
  window.open(href, '_blank');
}
function tabChange (value) {
  activeTab.value = value;
}

export {
  activeTab,
  testCaseProgress,
  tabChange,
  openReport,
  goTaskPage
};
