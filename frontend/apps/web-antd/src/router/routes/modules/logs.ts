import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('#/views/audit/index.vue'),
        meta: {
          authority: ['ADMIN'],
          title: $t('page.audit.title'),
        },
        name: 'AuditLogs',
        path: '/audit-logs',
      },
      {
        component: () => import('#/views/lease-events/index.vue'),
        meta: {
          title: $t('page.leaseEvents.title'),
        },
        name: 'LeaseEvents',
        path: '/lease-events',
      },
    ],
    meta: {
      icon: 'lucide:clipboard-list',
      order: 0,
      title: $t('page.logs.title'),
    },
    name: 'Logs',
    path: '/logs',
    redirect: '/lease-events',
  },
];

export default routes;
