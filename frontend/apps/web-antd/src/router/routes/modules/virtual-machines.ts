import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/virtual-machines/index.vue'),
    meta: {
      icon: 'lucide:monitor',
      order: 11,
      title: $t('page.virtualMachines.title'),
    },
    name: 'VirtualMachines',
    path: '/virtual-machines',
  },
  {
    component: () => import('#/views/virtual-machines/console.vue'),
    meta: {
      fullPathKey: false,
      hideInMenu: true,
      title: 'VM 控制台',
    },
    name: 'VirtualMachineConsole',
    path: '/virtual-machines/:resourceId/console',
  },
];

export default routes;
