/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/test-jobs/index.vue'),
    meta: {
      icon: 'lucide:flask-conical',
      order: 13,
      title: $t('page.testJobs.title'),
    },
    name: 'TestJobs',
    path: '/test-jobs/list',
  },
  {
    meta: { hideInMenu: true, title: '测试任务' },
    name: 'TestJobsRedirect',
    path: '/test-jobs',
    redirect: '/test-jobs/list',
  },
  {
    component: () => import('#/views/test-jobs/templates.vue'),
    meta: {
      hideInMenu: true,
      title: '任务模板',
    },
    name: 'TestJobTemplates',
    path: '/test-jobs/templates',
  },
  {
    component: () => import('#/views/test-jobs/detail.vue'),
    meta: {
      hideInMenu: true,
      title: '测试任务详情',
    },
    name: 'TestJobDetail',
    path: '/test-jobs/:jobId',
  },
];

export default routes;
