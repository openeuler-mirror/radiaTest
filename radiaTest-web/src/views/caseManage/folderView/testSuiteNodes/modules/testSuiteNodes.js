import { ref } from 'vue';
import router from '@/router';
const testSuiteProgress = [
  {
    label: '',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 80
  }
];

const documentList = ref([
  { id: '1', title: 'NestOS 22.03 LTS 版本测试策略', iframeUrl: 'https://www.baidu.com/' },
  { id: '2', title: 'OpenEuler 22.03 LTS 版本测试策略版本测试策略版本测试策略版本测试策略', iframeUrl: 'https://www.baidu.com/' },
  { id: '3', title: 'NestOS 22.03 LTS 版本测试策略', iframeUrl: 'https://www.baidu.com/' },
  { id: '4', title: 'NestOS 22.03 LTS 版本测试策略', iframeUrl: 'https://www.baidu.com/' },
]);

function documentInit() {
  //
  console.log('asffasfafas');
}

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
  testSuiteProgress,
  documentList,
  documentInit,
  openReport,
  createVersionTask,
  initData
};
