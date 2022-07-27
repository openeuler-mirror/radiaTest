import { ref } from 'vue';
import router from '@/router/index';

// tab名称
const menu = ref([
  {
    id: 1,
    text: '产品版本',
    name: 'product',
  },
  {
    id: 2,
    text: '里程碑',
    name: 'milestone',
  },
]);

const menuSelect = ref(0); // 当前页面索引值

// 页面切换
function menuClick(item, index) {
  menuSelect.value = index;
  router.push(`/home/version-management/${item.name}`);
}

const isTabActive = (name) => {
  return router.currentRoute.value.path.indexOf(name) !== -1;
};

export {
  menu,
  menuClick,
  isTabActive,
};
