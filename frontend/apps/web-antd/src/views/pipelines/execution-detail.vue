<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  PipelineExecutionRecord,
  PipelineExecutionSummary,
  PipelineSummaryRunJob,
  TestModuleTemplateRecord,
} from '#/api';

import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, RotateCw } from '@vben/icons';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  message,
  Modal,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  destroyExecutionEnvsApi,
  getExecutionSummaryApi,
  getModuleTemplatesApi,
  getPipelineExecutionApi,
} from '#/api';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const execution = ref<null | PipelineExecutionRecord>(null);
const summary = ref<null | PipelineExecutionSummary>(null);
const templates = ref<TestModuleTemplateRecord[]>([]);

interface MatrixRow {
  cells: Record<string, PipelineSummaryRunJob[]>;
  runId: string;
  version: string;
}

const templateMap = computed(() => {
  const map: Record<string, TestModuleTemplateRecord> = {};
  for (const t of templates.value) map[t.id] = t;
  return map;
});

const moduleList = computed(() => {
  const seen = new Map<string, TestModuleTemplateRecord>();
  for (const run of summary.value?.runs ?? []) {
    for (const job of run.jobs) {
      const t = templateMap.value[job.module_template_id];
      if (t && !seen.has(t.id)) seen.set(t.id, t);
    }
  }
  return [...seen.values()];
});

const archList = computed(() => summary.value?.archs ?? []);

function cellKey(moduleId: string, arch: string) {
  return `cell_${moduleId}_${arch}`;
}

function envTypeLabel(envType: null | string) {
  if (!envType) return 'VM';
  return envType === 'vm' ? 'VM' : '物理机';
}

const columns = computed<TableColumnsType>(() => {
  const moduleCols = moduleList.value.map((t) => {
    const archChildren = archList.value.map((arch) => ({
      align: 'center' as const,
      dataIndex: cellKey(t.id, arch),
      key: cellKey(t.id, arch),
      title: arch,
      width: 160,
    }));
    return {
      children: archChildren,
      dataIndex: `group_${t.id}`,
      key: `group_${t.id}`,
      title: t.display_name,
    };
  });
  return [
    {
      dataIndex: 'version',
      fixed: 'left' as const,
      key: 'version',
      title: '版本',
      width: 180,
    },
    ...moduleCols,
  ];
});

const matrixRows = computed<MatrixRow[]>(() => {
  const runs = summary.value?.runs ?? [];
  return runs.map((run) => {
    const cells: Record<string, PipelineSummaryRunJob[]> = {};
    for (const t of moduleList.value) {
      for (const arch of archList.value) {
        const key = cellKey(t.id, arch);
        cells[key] = run.jobs.filter(
          (j) => j.module_template_id === t.id && j.arch === arch,
        );
      }
    }
    return { cells, runId: run.id, version: run.version };
  });
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

function isEmpty(
  record: { cells?: Record<string, unknown[]> },
  column: { dataIndex?: unknown },
) {
  const raw = column.dataIndex as readonly string[] | string | undefined;
  const key = Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '');
  return !record.cells?.[key]?.length;
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    cancelled: '已取消',
    cancelling: '取消中',
    error: '异常',
    failed: '失败',
    pending: '待执行',
    preparing: '准备中',
    running: '执行中',
    succeeded: '成功',
    timeout: '超时',
  };
  return map[status] ?? status;
}

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function openRun(row: MatrixRow) {
  router.push(`/pipelines/runs/${row.runId}`);
}

function openRunJob(job: PipelineSummaryRunJob) {
  router.push(`/pipelines/run-jobs/${job.id}`);
}

async function loadExecution() {
  const id = route.params.id as string;
  loading.value = true;
  try {
    execution.value = await getPipelineExecutionApi(id);
    summary.value = await getExecutionSummaryApi(id);
    document.title = `执行: ${execution.value.config_name || execution.value.id.slice(0, 8)}`;
  } finally {
    loading.value = false;
  }
}

async function loadTemplates() {
  templates.value = await getModuleTemplatesApi();
}

async function refresh() {
  await loadExecution();
}

const destroying = ref(false);

function handleDestroyEnvs() {
  if (!execution.value) return;
  Modal.confirm({
    title: '销毁环境',
    content: `确定销毁 Execution ${execution.value.config_name} 的所有测试环境？VM 将被删除，物理机释放租约。此操作不可逆。`,
    okText: '销毁',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      const execId = execution.value?.id;
      if (!execId) return;
      destroying.value = true;
      try {
        await destroyExecutionEnvsApi(execId);
        message.success('销毁任务已提交，正在后台执行');
        await loadExecution();
      } catch {
        message.error('销毁失败');
      } finally {
        destroying.value = false;
      }
    },
  });
}

const autoRefreshTimer = ref<null | ReturnType<typeof setInterval>>(null);

const TERMINAL_STATUSES = new Set(['error', 'failed', 'succeeded']);

function stopAutoRefresh() {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value);
    autoRefreshTimer.value = null;
  }
}

function startAutoRefresh() {
  if (autoRefreshTimer.value) return;
  autoRefreshTimer.value = setInterval(() => void loadExecution(), 10_000);
}

onMounted(() => {
  void loadTemplates();
  void loadExecution();
  startAutoRefresh();
});

watch(
  () => execution.value?.status,
  (status: string | undefined) => {
    if (status && TERMINAL_STATUSES.has(status)) {
      stopAutoRefresh();
    } else {
      startAutoRefresh();
    }
  },
);

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<template>
  <Page title="流水线执行总览">
    <div class="space-y-4">
      <div class="flex items-center gap-3">
        <Button size="small" @click="router.push('/pipelines')">
          <template #icon><ArrowLeft class="size-4" /></template>
          返回
        </Button>
        <Button :loading="loading" size="small" @click="refresh">
          <template #icon><RotateCw class="size-4" /></template>
          刷新
        </Button>
        <Button
          danger
          size="small"
          :loading="destroying"
          @click="handleDestroyEnvs"
        >
          销毁环境
        </Button>
      </div>

      <Card v-if="execution" :body-style="{ padding: '16px' }">
        <Descriptions bordered :column="3" size="small">
          <DescriptionsItem label="配置名">
            {{ execution.config_name }}
          </DescriptionsItem>
          <DescriptionsItem label="状态">
            <Tag :color="statusColor(execution.status)">
              {{ statusLabel(execution.status) }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="触发者">
            {{ execution.triggered_by }}
          </DescriptionsItem>
          <DescriptionsItem label="触发时间">
            {{ formatTime(execution.triggered_at) }}
          </DescriptionsItem>
          <DescriptionsItem label="测试版本">
            <Tag
              v-for="v in execution.versions"
              :key="v"
              style="margin-bottom: 2px"
            >
              {{ v }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="架构">
            <Tag v-for="a in execution.archs" :key="a" color="blue">
              {{ a }}
            </Tag>
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <Card :body-style="{ padding: 0 }">
        <div class="px-4 pb-2 pt-3 text-base font-semibold">
          版本 × 模块 × 架构矩阵
        </div>
        <Table
          :columns="columns"
          :data-source="matrixRows"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: 'max-content' }"
          row-key="runId"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'version'">
              <Button
                type="link"
                size="small"
                @click="openRun(record as MatrixRow)"
              >
                {{ (record as MatrixRow).version }}
              </Button>
            </template>
            <template v-else-if="String(column.dataIndex).startsWith('cell_')">
              <div
                v-for="job in (record as MatrixRow).cells[
                  column.dataIndex as string
                ] ?? []"
                :key="job.id"
                class="pipeline-status-block"
                @click="openRunJob(job)"
              >
                <div
                  v-if="
                    (
                      (record as MatrixRow).cells[column.dataIndex as string] ??
                      []
                    ).length > 1
                  "
                  class="pipeline-env-label"
                >
                  {{ envTypeLabel(job.env_type) }}
                </div>
                <Tag
                  :color="statusColor(job.status)"
                  class="pipeline-status-chip"
                >
                  {{ statusLabel(job.status) }}
                </Tag>
                <div class="pipeline-status-counts">
                  <div
                    v-if="
                      job.counts.pending ||
                      job.counts.running ||
                      job.counts.not_executed
                    "
                    class="counts-row"
                  >
                    <span v-if="job.counts.pending">
                      待执行 {{ job.counts.pending }}
                    </span>
                    <span v-if="job.counts.running">
                      执行中 {{ job.counts.running }}
                    </span>
                    <span v-if="job.counts.not_executed">
                      未执行 {{ job.counts.not_executed }}
                    </span>
                  </div>
                  <div class="counts-row">
                    <span class="count-passed"
                      >通过 {{ job.counts.passed }}</span
                    >
                    <span class="count-failed"
                      >失败 {{ job.counts.failed }}</span
                    >
                    <span v-if="job.counts.error" class="count-failed">
                      异常 {{ job.counts.error }}
                    </span>
                    <span v-if="job.counts.timeout" class="count-failed">
                      超时 {{ job.counts.timeout }}
                    </span>
                    <span v-if="job.counts.skipped" class="count-skipped">
                      跳过 {{ job.counts.skipped }}
                    </span>
                    <span v-if="job.counts.no_case" class="count-skipped">
                      未找到用例 {{ job.counts.no_case }}
                    </span>
                  </div>
                </div>
              </div>
              <span v-if="isEmpty(record, column)" class="empty-cell">-</span>
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </Page>
</template>

<style scoped>
.pipeline-status-block {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 4px;
}

.pipeline-status-block:hover {
  background: rgb(0 0 0 / 5%);
}

.pipeline-env-label {
  font-size: 10px;
  line-height: 1;
  color: hsl(var(--muted-foreground));
}

.pipeline-status-chip {
  margin: 0;
}

.pipeline-status-counts {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  line-height: 1;
}

.counts-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.count-passed {
  color: hsl(var(--success));
}

.count-failed {
  color: hsl(var(--destructive));
}

.count-skipped {
  color: hsl(var(--muted-foreground));
}

.empty-cell {
  color: hsl(var(--muted-foreground));
}
</style>
