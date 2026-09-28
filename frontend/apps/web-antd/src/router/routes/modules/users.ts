import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/users/index.vue'),
    meta: {
      authority: ['ADMIN'],
      icon: 'lucide:users',
      order: 20,
      title: $t('page.users.title'),
    },
    name: 'Users',
    path: '/users',
  },
];

export default routes;
