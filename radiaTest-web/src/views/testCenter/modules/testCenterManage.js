import { ref } from 'vue';
import router from '@/router/index';

// tab名称
const menu = ref([
  {
    id: 1,
    text: '测试看板',
    name: 'jobs',
  },
  {
    id: 2,
    text: '模板仓库',
    name: 'template',
  },
]);

const menuSelect = ref(0); // 当前页面索引值

// 页面切换
function menuClick(item, index) {
  menuSelect.value = index;
  router.push(`/home/testing/${item.name}`);
}

const isTabActive = (name) => {
  return router.currentRoute.value.path.indexOf(name) !== -1;
};

export {
  menu,
  menuClick,
  isTabActive,
};
