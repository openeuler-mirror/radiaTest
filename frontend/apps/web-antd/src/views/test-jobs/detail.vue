<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  TaskEventRecord,
  TestCaseRunRecord,
  TestEnvNodeRecord,
  TestJobDetailRecord,
  TestJobRecord,
} from '#/api';

import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { useTabs } from '@vben/hooks';
import { ArrowLeft, ExternalLink, RotateCw } from '@vben/icons';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  message,
  Modal,
  Table,
  TabPane,
  Tabs,
  Tag,
} from 'ant-design-vue';

import { getTestJobApi, getTestJobEventsApi } from '#/api';

import TaskEventList from '../_shared/task-event-list.vue';
import { testStatusColor, testStatusLabel } from './test-job-view';

const route = useRoute();
const router = useRouter();
const { setTabTitle } = useTabs();
const loading = ref(false);
const job = ref<null | TestJobDetailRecord>(null);
const events = ref<TaskEventRecord[]>([]);
const activeEnvSet = ref('');
const selectedCaseRun = ref<null | TestCaseRunRecord>(null);
const outputOpen = ref(false);
const jobId = computed(() => Number(route.params.jobId));
const currentEnvSet = computed(() =>
  job.value?.env_sets.find((item) => item.id === activeEnvSet.value),
);

const nodeColumns: TableColumnsType<TestEnvNodeRecord> = [
  { dataIndex: 'node_index', title: '#', width: 60 },
  { dataIndex: 'role', title: '角色', width: 100 },
  { dataIndex: 'status', title: '状态', width: 100 },
  { dataIndex: 'primary_ip', title: 'OS IP', width: 150 },
  { dataIndex: 'resource_id', ellipsis: true, title: 'VM 资源', width: 260 },
  { key: 'action', title: '', width: 100 },
];

const caseColumns: TableColumnsType<TestCaseRunRecord> = [
  { dataIndex: 'suite_name', fixed: 'left', title: 'Suite', width: 220 },
  { dataIndex: 'case_name', ellipsis: true, title: 'Case', width: 280 },
  { dataIndex: 'status', title: '状态', width: 100 },
  { dataIndex: 'exit_code', title: '退出码', width: 90 },
  { dataIndex: 'started_at', title: '开始时间', width: 180 },
  { dataIndex: 'completed_at', title: '结束时间', width: 180 },
  { key: 'action', title: '', width: 90 },
];

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function displayValue(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function formatImage(record: TestJobRecord) {
  return [record.dist, record.os_version, record.image_round, record.arch]
    .filter(Boolean)
    .join(' / ');
}

async function loadDetail() {
  if (!Number.isInteger(jobId.value) || jobId.value < 1) {
    message.error('测试任务 ID 无效');
    await router.replace('/test-jobs/list');
    return;
  }
  loading.value = true;
  try {
    const [detail, taskEvents] = await Promise.all([
      getTestJobApi(jobId.value),
      getTestJobEventsApi(jobId.value),
    ]);
    job.value = detail;
    events.value = taskEvents;
    if (
      !activeEnvSet.value ||
      !detail.env_sets.some((item) => item.id === activeEnvSet.value)
    ) {
      activeEnvSet.value = detail.env_sets[0]?.id ?? '';
    }
    void setTabTitle(`任务 #${detail.id}`);
  } finally {
    loading.value = false;
  }
}

function openCaseOutput(record: TestCaseRunRecord) {
  selectedCaseRun.value = record;
  outputOpen.value = true;
}

async function openVM(record: TestEnvNodeRecord) {
  if (!record.resource_id) return;
  await router.push({
    path: '/virtual-machines',
    query: { vm_id: record.resource_id },
  });
}

function asNodeRecord(record: Record<string, unknown>) {
  return record as unknown as TestEnvNodeRecord;
}

function asCaseRunRecord(record: Record<string, unknown>) {
  return record as unknown as TestCaseRunRecord;
}

watch(jobId, () => void loadDetail(), { immediate: true });
</script>

<template>
  <Page :title="job?.name ?? `任务 #${jobId}`">
    <div class="min-w-0 space-y-4">
      <Button @click="router.push('/test-jobs/list')">
        <template #icon><ArrowLeft class="size-4" /></template>
        返回任务列表
      </Button>

      <Card v-if="job" :loading="loading">
        <div class="min-w-0 space-y-5">
          <Descriptions bordered :column="1" size="small">
            <DescriptionsItem label="任务 ID">{{ job.id }}</DescriptionsItem>
            <DescriptionsItem label="任务名称">{{ job.name }}</DescriptionsItem>
            <DescriptionsItem label="状态">
              <Tag :color="testStatusColor(job.status)">
                {{ testStatusLabel(job.status) }}
              </Tag>
            </DescriptionsItem>
            <DescriptionsItem label="创建人">
              {{ displayValue(job.creator_username) }}
            </DescriptionsItem>
            <DescriptionsItem label="镜像">
              {{ formatImage(job) }}
            </DescriptionsItem>
            <DescriptionsItem label="环境套数">
              {{ job.env_sets.length }}
            </DescriptionsItem>
            <DescriptionsItem label="保留失败环境">
              {{ job.keep_failed_env ? '是' : '否' }}
            </DescriptionsItem>
            <DescriptionsItem label="Mugen Commit">
              <span class="break-all">{{ job.mugen_commit_sha }}</span>
            </DescriptionsItem>
            <DescriptionsItem label="创建时间">
              {{ formatTime(job.created_at) }}
            </DescriptionsItem>
            <DescriptionsItem label="完成时间">
              {{ formatTime(job.completed_at) }}
            </DescriptionsItem>
            <DescriptionsItem label="错误码">
              {{ displayValue(job.error_code) }}
            </DescriptionsItem>
            <DescriptionsItem label="错误信息">
              <span class="whitespace-pre-wrap break-words">
                {{ displayValue(job.error_message) }}
              </span>
            </DescriptionsItem>
          </Descriptions>

          <section class="space-y-3 border-t border-border pt-4">
            <div class="text-base font-semibold">环境套</div>
            <div
              v-if="job.env_sets.length === 0"
              class="text-sm text-muted-foreground"
            >
              暂无环境套
            </div>
            <Tabs v-else v-model:active-key="activeEnvSet">
              <TabPane
                v-for="envSet in job.env_sets"
                :key="envSet.id"
                :tab="`环境 ${envSet.set_index}`"
              />
            </Tabs>
            <div v-if="currentEnvSet" class="min-w-0 space-y-4">
              <div class="management-toolbar__group">
                <Tag :color="testStatusColor(currentEnvSet.status)">
                  {{ testStatusLabel(currentEnvSet.status) }}
                </Tag>
                <Tag>{{ currentEnvSet.node_num }} 节点</Tag>
                <Tag>{{ currentEnvSet.add_disk_num }} 块额外数据盘</Tag>
                <Tag>{{ currentEnvSet.add_nic_num }} 张额外网卡</Tag>
              </div>

              <div class="text-sm font-semibold">节点</div>
              <Table
                :columns="nodeColumns"
                :data-source="currentEnvSet.nodes"
                :pagination="false"
                :scroll="{ x: 820 }"
                row-key="id"
                size="small"
              >
                <template #bodyCell="{ column, record, text }">
                  <template v-if="column.dataIndex === 'status'">
                    <Tag :color="testStatusColor(record.status)">
                      {{ testStatusLabel(record.status) }}
                    </Tag>
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <Button
                      v-if="record.resource_id && record.status !== 'destroyed'"
                      size="small"
                      type="link"
                      @click="openVM(asNodeRecord(record))"
                    >
                      <template #icon><ExternalLink class="size-4" /></template>
                      查看 VM
                    </Button>
                  </template>
                  <template v-else>{{ displayValue(text) }}</template>
                </template>
              </Table>

              <div class="text-sm font-semibold">Case 结果</div>
              <Table
                :columns="caseColumns"
                :data-source="currentEnvSet.case_runs"
                :pagination="{ defaultPageSize: 20, showSizeChanger: true }"
                :scroll="{ x: 1220 }"
                row-key="id"
                size="small"
              >
                <template #bodyCell="{ column, record, text }">
                  <template v-if="column.dataIndex === 'status'">
                    <Tag :color="testStatusColor(record.status)">
                      {{ testStatusLabel(record.status) }}
                    </Tag>
                  </template>
                  <template
                    v-else-if="
                      ['started_at', 'completed_at'].includes(
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
                      @click="openCaseOutput(asCaseRunRecord(record))"
                    >
                      输出
                    </Button>
                  </template>
                </template>
              </Table>
            </div>
          </section>

          <section class="space-y-3 border-t border-border pt-4">
            <div class="text-base font-semibold">任务事件</div>
            <TaskEventList
              :events="events"
              :loading="loading"
              :show-refresh="false"
            />
          </section>

          <div class="flex justify-end border-t border-border pt-4">
            <Button :loading="loading" @click="loadDetail">
              <template #icon><RotateCw class="size-4" /></template>
              刷新
            </Button>
          </div>
        </div>
      </Card>
    </div>

    <Modal
      v-model:open="outputOpen"
      :footer="null"
      destroy-on-close
      title="Case 输出摘要"
      width="min(900px, calc(100vw - 32px))"
    >
      <div v-if="selectedCaseRun" class="space-y-4">
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="Case">
            {{ selectedCaseRun.suite_name }}/{{ selectedCaseRun.case_name }}
          </DescriptionsItem>
          <DescriptionsItem label="状态">
            {{ testStatusLabel(selectedCaseRun.status) }}
          </DescriptionsItem>
          <DescriptionsItem label="退出码">
            {{ displayValue(selectedCaseRun.exit_code) }}
          </DescriptionsItem>
        </Descriptions>
        <section>
          <div class="mb-2 text-sm font-semibold">stdout</div>
          <pre class="management-json rounded bg-muted p-3">{{
            displayValue(selectedCaseRun.stdout_summary)
          }}</pre>
        </section>
        <section>
          <div class="mb-2 text-sm font-semibold">stderr</div>
          <pre class="management-json rounded bg-muted p-3">{{
            displayValue(selectedCaseRun.stderr_summary)
          }}</pre>
        </section>
      </div>
    </Modal>
  </Page>
</template>
