<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type {
  MugenCaseRecord,
  TestJobDetailRecord,
  TestJobRecord,
  VMImageRecord,
} from '#/api';

import { onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Eye, Plus, RotateCw } from '@vben/icons';

import { Button, Card, Checkbox, message, Table, Tag } from 'ant-design-vue';

import { getAllTestCasesApi, getTestJobsApi, getVMImagesApi } from '#/api';

import { createLatestRequestGuard } from '../_shared/latest-request';
import { tablePagination } from '../_shared/table-pagination';
import TestJobCreateModal from './test-job-create-modal.vue';
import { testStatusColor, testStatusLabel } from './test-job-view';
import TestJobsTabs from './test-jobs-tabs.vue';

const router = useRouter();
const jobListRequest = createLatestRequestGuard();
const loading = ref(false);
const createLoading = ref(false);
const createOpen = ref(false);
const showAll = ref(false);
const jobs = ref<TestJobRecord[]>([]);
const jobPage = ref(1);
const jobTotal = ref(0);
const cases = ref<MugenCaseRecord[]>([]);
const images = ref<VMImageRecord[]>([]);

const columns: TableColumnsType<TestJobRecord> = [
  { dataIndex: 'id', fixed: 'left', title: 'ID', width: 90 },
  {
    dataIndex: 'name',
    ellipsis: true,
    fixed: 'left',
    title: '任务名称',
    width: 220,
  },
  { dataIndex: 'status', title: '状态', width: 110 },
  { dataIndex: 'creator_username', title: '创建人', width: 120 },
  { key: 'image', title: '测试镜像', width: 360 },
  { dataIndex: 'env_set_num', title: '环境套数', width: 100 },
  { dataIndex: 'keep_failed_env', title: '保留失败环境', width: 130 },
  { dataIndex: 'created_at', title: '创建时间', width: 180 },
  { dataIndex: 'completed_at', title: '完成时间', width: 180 },
  { dataIndex: 'error_message', ellipsis: true, title: '错误', width: 240 },
  { fixed: 'right', key: 'action', title: '', width: 90 },
];

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function formatImage(record: TestJobRecord) {
  return [record.dist, record.os_version, record.image_round, record.arch]
    .filter(Boolean)
    .join(' / ');
}

async function loadJobs() {
  const request = jobListRequest.begin();
  loading.value = true;
  try {
    const response = await getTestJobsApi(showAll.value, jobPage.value);
    request.commit(() => {
      jobs.value = response.items;
      jobTotal.value = response.total;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

async function openCreate() {
  createLoading.value = true;
  try {
    [cases.value, images.value] = await Promise.all([
      getAllTestCasesApi({ env_type: 'vm' }),
      getVMImagesApi(),
    ]);
  } finally {
    createLoading.value = false;
  }
  if (cases.value.length === 0) {
    message.warning('当前没有可用的 VM 测试用例，请先同步 Mugen 索引');
    return;
  }
  if (images.value.length === 0) {
    message.warning('当前没有可用的 VM 镜像');
    return;
  }
  createOpen.value = true;
}

async function handleCreated(job: TestJobDetailRecord) {
  await router.push(`/test-jobs/${job.id}`);
}

function asTestJobRecord(record: Record<string, unknown>) {
  return record as unknown as TestJobRecord;
}

function changePage(pagination: TablePaginationConfig) {
  jobPage.value = pagination.current ?? 1;
  void loadJobs();
}

watch(showAll, () => {
  jobPage.value = 1;
  void loadJobs();
});
onMounted(() => void loadJobs());
</script>

<template>
  <Page title="测试任务">
    <div class="space-y-4">
      <TestJobsTabs />

      <Card :body-style="{ padding: '16px' }">
        <div class="management-toolbar">
          <div class="management-toolbar__group">
            <Checkbox v-model:checked="showAll">查看全部</Checkbox>
            <Tag>{{ jobTotal }} 个任务</Tag>
          </div>
          <div class="management-toolbar__actions management-toolbar__group">
            <Button :loading="loading" @click="loadJobs">
              <template #icon><RotateCw class="size-4" /></template>
              刷新
            </Button>
            <Button :loading="createLoading" type="primary" @click="openCreate">
              <template #icon><Plus class="size-4" /></template>
              创建任务
            </Button>
          </div>
        </div>
      </Card>

      <Card class="management-table-card" :body-style="{ padding: 0 }">
        <Table
          :columns="columns"
          :data-source="jobs"
          :loading="loading"
          :pagination="tablePagination(jobPage, jobTotal)"
          :scroll="{ x: 1800 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'status'">
              <Tag :color="testStatusColor(record.status)">
                {{ testStatusLabel(record.status) }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'image'">
              {{ formatImage(asTestJobRecord(record)) }}
            </template>
            <template v-else-if="column.dataIndex === 'keep_failed_env'">
              {{ record.keep_failed_env ? '是' : '否' }}
            </template>
            <template
              v-else-if="
                ['created_at', 'completed_at'].includes(
                  String(column.dataIndex),
                )
              "
            >
              {{ formatTime(text) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Button
                size="small"
                type="link"
                @click="router.push(`/test-jobs/${record.id}`)"
              >
                <template #icon><Eye class="size-4" /></template>
                详情
              </Button>
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <TestJobCreateModal
      v-model:open="createOpen"
      :cases="cases"
      :images="images"
      purpose="create-job"
      @job-created="handleCreated"
    />
  </Page>
</template>
