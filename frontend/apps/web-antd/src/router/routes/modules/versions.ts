import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/rc-management/index.vue'),
    meta: {
      icon: 'lucide:boxes',
      order: 16,
      title: '版本管理',
    },
    name: 'Versions',
    path: '/versions',
  },
  {
    component: () => import('#/views/rc-management/version-detail.vue'),
    meta: {
      hideInMenu: true,
      title: '版本详情',
    },
    name: 'VersionDetail',
    path: '/versions/:id',
  },
  {
    component: () => import('#/views/rc-management/milestone-console.vue'),
    meta: {
      hideInMenu: true,
      title: '轮次测试控制台',
    },
    name: 'MilestoneConsole',
    path: '/versions/:id/milestones/:milestoneId',
  },
];

export default routes;
