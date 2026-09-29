import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/tickets/index.vue'),
    meta: {
      icon: 'lucide:ticket-check',
      order: 14,
      title: $t('page.tickets.title'),
    },
    name: 'Tickets',
    path: '/tickets',
  },
  {
    component: () => import('#/views/tickets/detail.vue'),
    meta: {
      hideInMenu: true,
      title: '工单详情',
    },
    name: 'TicketDetail',
    path: '/tickets/:ticketId',
  },
];

export default routes;
