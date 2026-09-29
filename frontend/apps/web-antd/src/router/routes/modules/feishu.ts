import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/feishu/index.vue'),
    meta: {
      authority: ['ADMIN'],
      icon: 'lucide:bot',
      order: 30,
      title: $t('page.feishu.title'),
    },
    name: 'FeishuIntegration',
    path: '/integrations/feishu',
  },
];

export default routes;
