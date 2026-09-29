import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/account/index.vue'),
    meta: {
      icon: 'lucide:user-round',
      order: 50,
      title: $t('page.account.title'),
    },
    name: 'Account',
    path: '/account',
  },
];

export default routes;
