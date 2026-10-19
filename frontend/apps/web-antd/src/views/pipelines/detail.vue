<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  PipelineRunJobRecord,
  PipelineRunNodeInfoRecord,
  PipelineRunRecord,
  TestModuleTemplateRecord,
} from '#/api';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, ExternalLink, RotateCw } from '@vben/icons';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  getModuleTemplatesApi,
  getPipelineRunApi,
  getPipelineRunJobsApi,
  getRunJobNodesApi,
} from '#/api';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const jobsLoading = ref(false);
const run = ref<null | PipelineRunRecord>(null);
const jobs = ref<PipelineRunJobRecord[]>([]);
const templates = ref<TestModuleTemplateRecord[]>([]);
const nodeMap = ref<Record<string, PipelineRunNodeInfoRecord[]>>({});

interface ModuleRow {
  jobsByArch: Record<string, PipelineRunJobRecord[]>;
  template: TestModuleTemplateRecord;
}

const templateMap = computed(() => {
  const map: Record<string, TestModuleTemplateRecord> = {};
  for (const t of templates.value) map[t.id] = t;
  return map;
});

const archList = computed(() => {
  const archs: string[] = [];
  for (const job of jobs.value) {
    if (!archs.includes(job.arch)) archs.push(job.arch);
  }
  return archs;
});

const moduleRows = computed<ModuleRow[]>(() => {
  const seen = new Map<string, TestModuleTemplateRecord>();
  for (const job of jobs.value) {
    const t = templateMap.value[job.module_template_id];
    if (t && !seen.has(t.id)) seen.set(t.id, t);
  }
  const rows: ModuleRow[] = [];
  for (const t of seen.values()) {
    const jobsByArch: Record<string, PipelineRunJobRecord[]> = {};
    for (const arch of archList.value) {
      jobsByArch[arch] = jobs.value.filter(
        (j) => j.module_template_id === t.id && j.arch === arch,
      );
    }
    rows.push({ jobsByArch, template: t });
  }
  return rows;
});

const columns = computed<TableColumnsType>(() => {
  const archCols = archList.value.map((arch) => ({
    dataIndex: `arch_${arch}`,
    key: `arch_${arch}`,
    title: arch,
    width: 320,
  }));
  return [
    {
      dataIndex: 'module',
      fixed: 'left' as const,
      key: 'module',
      title: '模块',
      width: 160,
    },
    ...archCols,
  ];
});

function statusColor(status: string) {
  const map: Record<string, string> = {
    cancelled: 'default',
    cancelling: 'warning',
    error: 'orange',
    failed: 'red',
    pending: 'default',
    preparing: 'cyan',
    running: 'processing',
    succeeded: 'green',
    timeout: 'default',
  };
  return map[status] ?? 'default';
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    cancelled: '已取消',
    cancelling: '取消中',
    error: '异常',
    failed: '失败',
    pending: '等待',
    preparing: '准备中',
    running: '执行中',
    succeeded: '成功',
    timeout: '超时',
  };
  return map[status] ?? status;
}

function envTypeLabel(envType: null | string) {
  if (!envType) return 'VM';
  return envType === 'vm' ? 'VM' : '物理机';
}

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function getNodes(job: PipelineRunJobRecord) {
  return nodeMap.value[job.id] ?? [];
}

function openVM(resourceId: null | string) {
  if (!resourceId) return;
  router.push({
    path: '/virtual-machines',
    query: { vm_id: resourceId },
  });
}

function openRunJob(job: PipelineRunJobRecord) {
  router.push(`/pipelines/run-jobs/${job.id}`);
}

async function loadRun() {
  const id = route.params.id as string;
  loading.value = true;
  try {
    run.value = await getPipelineRunApi(id);
  } finally {
    loading.value = false;
  }
}

async function loadJobs() {
  const id = route.params.id as string;
  jobsLoading.value = true;
  try {
    jobs.value = await getPipelineRunJobsApi(id);
    await Promise.all(
      jobs.value.map(async (j) => {
        try {
          nodeMap.value[j.id] = await getRunJobNodesApi(id, j.id);
        } catch {
          nodeMap.value[j.id] = [];
        }
      }),
    );
  } finally {
    jobsLoading.value = false;
  }
}

async function loadTemplates() {
  templates.value = await getModuleTemplatesApi();
}

async function refresh() {
  await Promise.all([loadRun(), loadJobs()]);
}

onMounted(() => {
  void loadRun();
  void loadJobs();
  void loadTemplates();
});
</script>

<template>
  <Page title="版本子流水线详情">
    <div class="space-y-4">
      <div class="flex items-center gap-3">
        <Button size="small" @click="router.back()">
          <template #icon><ArrowLeft class="size-4" /></template>
          返回
        </Button>
        <Button :loading="loading" size="small" @click="refresh">
          <template #icon><RotateCw class="size-4" /></template>
          刷新
        </Button>
      </div>

      <Card v-if="run" :body-style="{ padding: '16px' }">
        <Descriptions bordered :column="3" size="small">
          <DescriptionsItem label="版本">{{ run.version }}</DescriptionsItem>
          <DescriptionsItem label="状态">
            <Tag :color="statusColor(run.status)">
              {{ statusLabel(run.status) }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="触发者">
            {{ run.triggered_by }}
          </DescriptionsItem>
          <DescriptionsItem label="触发时间">
            {{ formatTime(run.triggered_at) }}
          </DescriptionsItem>
          <DescriptionsItem label="完成时间">
            {{ formatTime(run.completed_at) }}
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <Card :body-style="{ padding: 0 }">
        <div class="px-4 pb-2 pt-3 text-base font-semibold">
          模块 × 架构矩阵
        </div>
        <Table
          :columns="columns"
          :data-source="moduleRows"
          :loading="jobsLoading"
          :pagination="false"
          :scroll="{ x: 'max-content' }"
          row-key="template.id"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'module'">
              {{ (record as ModuleRow).template.display_name }}
              <div style="font-size: 11px; color: hsl(var(--muted-foreground))">
                {{ (record as ModuleRow).template.suite_name }}
              </div>
            </template>
            <template v-else-if="String(column.dataIndex).startsWith('arch_')">
              <div
                v-for="job in (record as ModuleRow).jobsByArch[
                  String(column.dataIndex).replace('arch_', '')
                ] ?? []"
                :key="job.id"
                class="pipeline-cell"
              >
                <div
                  v-if="
                    (
                      (record as ModuleRow).jobsByArch[
                        String(column.dataIndex).replace('arch_', '')
                      ] ?? []
                    ).length > 1
                  "
                  class="pipeline-env-label"
                >
                  {{ envTypeLabel(job.env_type) }}
                </div>
                <div class="pipeline-cell-header" @click="openRunJob(job)">
                  <Tag :color="statusColor(job.status)">
                    {{ statusLabel(job.status) }}
                  </Tag>
                </div>
                <div class="pipeline-ip-tags">
                  <Tag
                    v-for="node in getNodes(job)"
                    :key="node.id"
                    :color="
                      node.status === 'ready'
                        ? 'green'
                        : node.status === 'error'
                          ? 'red'
                          : 'blue'
                    "
                    style="margin-bottom: 2px; cursor: pointer"
                    @click="openVM(node.resource_id)"
                  >
                    {{ node.primary_ip || '-' }}
                    <span class="node-role">({{ node.role }})</span>
                    <template v-if="node.resource_id">
                      <ExternalLink class="ml-1 inline-block size-3" />
                    </template>
                  </Tag>
                  <span
                    v-if="getNodes(job).length === 0"
                    style="font-size: 12px; color: hsl(var(--muted-foreground))"
                  >
                    尚未创建
                  </span>
                </div>
              </div>
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </Page>
</template>

<style scoped>
.pipeline-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
}

.pipeline-cell-header {
  cursor: pointer;
}

.pipeline-env-label {
  font-size: 10px;
  line-height: 1;
  color: hsl(var(--muted-foreground));
}

.pipeline-ip-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.node-role {
  font-size: 10px;
  color: hsl(var(--muted-foreground));
}
</style>
