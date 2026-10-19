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
    component: () => import('#/views/pipelines/index.vue'),
    meta: {
      icon: 'lucide:git-branch',
      order: 15,
      title: $t('page.pipelines.title'),
    },
    name: 'Pipelines',
    path: '/pipelines',
  },
  {
    component: () => import('#/views/pipelines/config-detail.vue'),
    meta: {
      hideInMenu: true,
      title: '流水线配置详情',
    },
    name: 'PipelineConfigDetail',
    path: '/pipelines/configs/:id/executions',
  },
  {
    component: () => import('#/views/pipelines/execution-detail.vue'),
    meta: {
      hideInMenu: true,
      title: '执行详情',
    },
    name: 'PipelineExecutionDetail',
    path: '/pipelines/executions/:id',
  },
  {
    component: () => import('#/views/pipelines/detail.vue'),
    meta: {
      hideInMenu: true,
      title: 'Run 详情',
    },
    name: 'PipelineRunDetail',
    path: '/pipelines/runs/:id',
  },
  {
    component: () => import('#/views/pipelines/run-job-detail.vue'),
    meta: {
      hideInMenu: true,
      title: 'RunJob 详情',
    },
    name: 'PipelineRunJobDetail',
    path: '/pipelines/run-jobs/:id',
  },
  {
    component: () => import('#/views/pipelines/case-log.vue'),
    meta: {
      hideInMenu: true,
      title: 'Mugen 日志',
    },
    name: 'PipelineCaseLog',
    path: '/pipelines/run-jobs/:id/cases/:caseRunId/log',
  },
  {
    component: () => import('#/views/pipelines/log-viewer.vue'),
    meta: {
      hideInMenu: true,
      title: '日志查看',
    },
    name: 'PipelineLogViewer',
    path: '/pipelines/runs/:runId/logs/:artifactId',
  },
  {
    component: () => import('#/views/pipelines/folder-browser.vue'),
    meta: {
      hideInMenu: true,
      title: '文件夹浏览',
    },
    name: 'PipelineFolderBrowser',
    path: '/pipelines/runs/:runId/logs/:artifactId/folder',
  },
];

export default routes;
