import { ref } from 'vue';
import router from '@/router/index.js';
import management from './management';
const tableView = ref(false);
function setMenu() {
  if (tableView.value) {
    management.menu.value = [
      {
        id: 0,
        text: '测试套仓库',
        name: 'testsuite',
      },
      {
        id: 1,
        text: '用例仓库',
        name: 'testcase',
      },

      {
        id: 3,
        text: '测试框架',
        name: 'frameWork',
      },
    ];
  } else {
    management.menu.value = [
      {
        id: 1,
        text: '用例仓库',
        name: 'folderview',
      },

      {
        id: 3,
        text: '测试框架',
        name: 'frameWork',
      },
    ];
  }
}
function toggleView() {
  tableView.value = !tableView.value;
  if (tableView.value) {
    router.push({ name: 'testcase' });
    setMenu();
  } else {
    router.push({ name: 'folderview' });
    setMenu();
  }
}
export default {
  tableView,
  toggleView,
  setMenu,
};
