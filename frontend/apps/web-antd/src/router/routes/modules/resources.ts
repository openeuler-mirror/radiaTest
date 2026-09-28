import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/resources/index.vue'),
    meta: {
      icon: 'lucide:server',
      order: 10,
      title: $t('page.resources.title'),
    },
    name: 'Resources',
    path: '/resources',
  },
];

export default routes;
