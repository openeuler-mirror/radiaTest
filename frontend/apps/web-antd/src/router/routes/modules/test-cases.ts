import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/test-cases/index.vue'),
    meta: {
      icon: 'lucide:list-checks',
      order: 12,
      title: $t('page.testCases.title'),
    },
    name: 'TestCases',
    path: '/test-cases',
  },
];

export default routes;
