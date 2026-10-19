<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type {
  PipelineTestCaseRunRecord,
  RunJobDetail,
  TestModuleTemplateRecord,
} from '#/api';

import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, ExternalLink, RotateCw } from '@vben/icons';

import {
  Button,
  Card,
  Collapse,
  CollapsePanel,
  Descriptions,
  DescriptionsItem,
  Input,
  message,
  Select,
  SelectOption,
  Tag,
  Tooltip,
} from 'ant-design-vue';

import {
  cancelRunJobApi,
  getModuleTemplatesApi,
  getRunJobDetailApi,
} from '#/api';

import CaseRerunModal from './case-rerun-modal.vue';
import { finishedCaseCount, totalCaseCount } from './run-job-case-stats';
import { isRunJobTerminalStatus } from './run-job-terminal-status';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const detail = ref<null | RunJobDetail>(null);
const templates = ref<TestModuleTemplateRecord[]>([]);

const caseFilter = ref<
  | 'all'
  | 'error'
  | 'failed'
  | 'no_case'
  | 'not_executed'
  | 'passed'
  | 'skipped'
  | 'timeout'
>('all');
const caseSearch = ref('');
const timelineExpanded = ref(false);
const rerunModalOpen = ref(false);
const cancelling = ref(false);

const canCancel = computed(() => {
  const status = detail.value?.status;
  return status === 'running' || status === 'preparing' || status === 'pending';
});

const templateMap = computed(() => {
  const map: Record<string, TestModuleTemplateRecord> = {};
  for (const t of templates.value) map[t.id] = t;
  return map;
});

const moduleName = computed(() => {
  if (!detail.value) return '-';
  const t = templateMap.value[detail.value.module_template_id];
  return t?.display_name ?? t?.name ?? '-';
});

// pkgunion 与 pkgcmd 同为逐 case 结果形态（ADR 0021 语义），隐藏右栏全宽展示用例列表
const isPkgcmd = computed(
  () =>
    detail.value?.result_parser === 'pkgcmd' ||
    detail.value?.result_parser === 'pkgunion',
);

const caseStats = computed(() => {
  const empty = {
    total: 0,
    passed: 0,
    failed: 0,
    skipped: 0,
    no_case: 0,
    toExecute: 0,
    notExecuted: 0,
    running: 0,
    error: 0,
    timeout: 0,
    foundPackages: 0,
  };
  if (!detail.value) return empty;
  const cases = detail.value.case_runs ?? [];
  const count = (s: string) => cases.filter((c) => c.status === s).length;
  return {
    // 总计排除 no_case（未找到用例的包，包维度归"包行"），保证总计=各状态计数之和
    total: totalCaseCount(cases),
    passed: count('passed'),
    failed: count('failed'),
    skipped: count('skipped'),
    no_case: count('no_case'),
    // 待执行 = pending（会跑、排队中），不含 not_executed（不会跑）
    toExecute: count('pending'),
    // 未执行 = not_executed（物理机开关关 / 64k 未转测，不会跑），独立于跳过与待执行
    notExecuted: count('not_executed'),
    running: count('running'),
    error: count('error'),
    timeout: count('timeout'),
    // 找到用例的包数 = 有非 no_case case 的 suite 数（pkgcmd 下 suite 即包名）
    foundPackages: new Set(
      cases.filter((c) => c.status !== 'no_case').map((c) => c.suite_name),
    ).size,
  };
});

const filteredCases = computed<PipelineTestCaseRunRecord[]>(() => {
  if (!detail.value) return [];
  const list = detail.value.case_runs ?? [];
  const filter = caseFilter.value;
  const keyword = caseSearch.value.trim().toLowerCase();
  return list.filter((c) => {
    if (filter !== 'all' && c.status !== filter) return false;
    if (!keyword) return true;
    const suite = (c.suite_name ?? '').toLowerCase();
    const name = (c.case_name ?? '').toLowerCase();
    return suite.includes(keyword) || name.includes(keyword);
  });
});

const groupedCases = computed(() => {
  const groups: Record<
    string,
    {
      cases: PipelineTestCaseRunRecord[];
      envTypes: Set<string>;
      error: number;
      failed: number;
      no_case: number;
      not_executed: number;
      passed: number;
      skipped: number;
      suite: string;
      timeout: number;
    }
  > = {};
  for (const cr of filteredCases.value) {
    const suite = cr.suite_name ?? '-';
    if (!groups[suite]) {
      groups[suite] = {
        suite,
        cases: [],
        passed: 0,
        failed: 0,
        error: 0,
        skipped: 0,
        timeout: 0,
        no_case: 0,
        not_executed: 0,
        envTypes: new Set(),
      };
    }
    groups[suite].cases.push(cr);
    switch (cr.status) {
      case 'error': {
        groups[suite].error++;
        break;
      }
      case 'failed': {
        groups[suite].failed++;
        break;
      }
      case 'no_case': {
        groups[suite].no_case++;
        break;
      }
      case 'not_executed': {
        groups[suite].not_executed++;
        // No default
        break;
      }
      case 'passed': {
        groups[suite].passed++;
        break;
      }
      case 'skipped': {
        groups[suite].skipped++;
        break;
      }
      case 'timeout': {
        groups[suite].timeout++;
        break;
      }
    }
    if (cr.env_type) groups[suite].envTypes.add(cr.env_type);
  }
  return Object.values(groups);
});

const visibleTaskEvents = computed(() => {
  if (!detail.value?.task_events) return [];
  if (timelineExpanded.value) return detail.value.task_events;
  return [...detail.value.task_events].toReversed().slice(0, 3).toReversed();
});

const mugenLogs = computed(() => {
  if (!detail.value?.logs) return [];
  return detail.value.logs.filter((l) => l.artifact_type === 'module_log');
});

const folderArtifacts = computed(() => {
  if (!detail.value?.logs) return [];
  return detail.value.logs.filter((l) => l.artifact_type === 'pkg_folder');
});

const isPkgmanage = computed(() => detail.value?.result_parser === 'pkgmanage');

const reportArtifacts = computed(() => {
  if (!detail.value?.logs) return [];
  return detail.value.logs.filter(
    (l) =>
      l.artifact_type === 'module_log' &&
      l.artifact_name.includes('pkgmanage-details'),
  );
});

function statusColor(status: string) {
  const map: Record<string, string> = {
    cancelled: 'default',
    cancelling: 'warning',
    error: 'orange',
    failed: 'red',
    passed: 'green',
    pending: 'default',
    preparing: 'cyan',
    running: 'processing',
    skipped: 'default',
    no_case: 'default',
    not_executed: 'default',
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
    passed: '通过',
    pending: '待执行',
    preparing: '准备中',
    running: '执行中',
    skipped: '跳过',
    no_case: '未找到用例',
    not_executed: '未执行',
    succeeded: '成功',
    timeout: '超时',
  };
  return map[status] ?? status;
}

function isUniform(
  group: { cases: PipelineTestCaseRunRecord[] },
  status: string,
) {
  // suite 下全部用例同属一个状态（如全 no_case=没找到用例的包、全 not_executed=物理机不执行、
  // 全 skipped=mugen 跳过、全 pending=待执行）。这类 suite 分组头直接显状态标签，不走"通过 a/x"。
  return (
    group.cases.length > 0 && group.cases.every((c) => c.status === status)
  );
}

function isInProgress(group: { cases: PipelineTestCaseRunRecord[] }) {
  // 执行中：有 running（正在跑）或有 pending（已排队未跑）但非全 pending（全 pending 走"待执行"）。
  // 这种混合 suite 显"执行中 a/x"蓝底，而非"通过 a/x"红底（passed<total 会误显红=失败）。
  const hasRunning = group.cases.some((c) => c.status === 'running');
  const hasPending = group.cases.some((c) => c.status === 'pending');
  return hasRunning || hasPending;
}

function envTypeLabel(envType: null | string) {
  if (!envType) return 'VM';
  return envType === 'vm' ? 'VM' : '物理机';
}

function formatEventTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function eventColor(level: string) {
  if (level === 'error') return 'red';
  if (level === 'warning') return 'orange';
  return 'blue';
}

function openNode(resourceId: null | string, envType: null | string) {
  if (!resourceId) return;
  const isPhysical = envType === 'physical';
  router.push({
    path: isPhysical ? '/resources' : '/virtual-machines',
    query: isPhysical ? { resource_id: resourceId } : { vm_id: resourceId },
  });
}

function openLog(artifactId: string) {
  if (!detail.value) return;
  router.push(
    `/pipelines/runs/${detail.value.pipeline_run_id}/logs/${artifactId}`,
  );
}

function openFolder(artifactId: string) {
  if (!detail.value) return;
  router.push(
    `/pipelines/runs/${detail.value.pipeline_run_id}/logs/${artifactId}/folder`,
  );
}

function openCaseLog(caseRunId: string) {
  const runJobId = route.params.id as string;
  router.push(`/pipelines/run-jobs/${runJobId}/cases/${caseRunId}/log`);
}

function openRerunModal() {
  if (detail.value?.can_rerun) rerunModalOpen.value = true;
}

async function handleRerunCreated(runJobId: string) {
  rerunModalOpen.value = false;
  await router.push(`/pipelines/run-jobs/${runJobId}`);
}

async function handleCancel() {
  const id = route.params.id as string;
  cancelling.value = true;
  try {
    await cancelRunJobApi(id);
    await loadDetail();
  } catch {
    message.error('取消请求失败');
  } finally {
    cancelling.value = false;
  }
}

async function loadDetail() {
  const id = route.params.id as string;
  loading.value = true;
  try {
    detail.value = await getRunJobDetailApi(id);
    document.title = `RunJob: ${moduleName.value}/${detail.value.arch}`;
  } finally {
    loading.value = false;
  }
}

async function loadTemplates() {
  templates.value = await getModuleTemplatesApi();
}

async function refresh() {
  await loadDetail();
}

const autoRefreshTimer = ref<null | ReturnType<typeof setInterval>>(null);

function stopAutoRefresh() {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value);
    autoRefreshTimer.value = null;
  }
}

function startAutoRefresh() {
  if (autoRefreshTimer.value) return;
  autoRefreshTimer.value = setInterval(() => void loadDetail(), 10_000);
}

onMounted(() => {
  void loadTemplates();
  void loadDetail();
  startAutoRefresh();
});

watch(
  () => route.params.id,
  () => void loadDetail(),
);

watch(
  () => detail.value?.status,
  (status) => {
    if (isRunJobTerminalStatus(status)) {
      stopAutoRefresh();
    } else {
      startAutoRefresh();
    }
  },
);

onUnmounted(() => {
  stopAutoRefresh();
});

watch(
  () => route.params.id,
  () => void loadDetail(),
);
</script>

<template>
  <Page title="RunJob 详情">
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
        <Tooltip :title="detail?.rerun_unavailable_reason ?? undefined">
          <span>
            <Button
              :disabled="!detail?.can_rerun"
              size="small"
              type="primary"
              @click="openRerunModal"
            >
              用例重跑
            </Button>
          </span>
        </Tooltip>
        <Button
          v-if="canCancel"
          :loading="cancelling"
          danger
          size="small"
          @click="handleCancel"
        >
          中止
        </Button>
      </div>

      <CaseRerunModal
        v-if="rerunModalOpen && detail"
        :cases="detail.rerun_candidates"
        :run-job-id="detail.id"
        @close="rerunModalOpen = false"
        @created="handleRerunCreated($event.id)"
      />

      <Card
        v-if="detail?.rerun_chain.length"
        :body-style="{ padding: '12px 16px' }"
      >
        <div class="mb-2 text-sm font-semibold">执行历史</div>
        <div class="run-history">
          <button
            v-for="item in detail.rerun_chain"
            :key="item.id"
            class="run-history__item"
            :class="{ 'run-history__item--active': item.id === detail.id }"
            type="button"
            @click="router.push(`/pipelines/run-jobs/${item.id}`)"
          >
            <span class="run-history__marker"></span>
            <span class="run-history__title">
              {{
                item.rerun_attempt === 0
                  ? '首次执行'
                  : `第 ${item.rerun_attempt} 次重跑`
              }}
            </span>
            <Tag :color="statusColor(item.status)" class="m-0">
              {{ statusLabel(item.status) }}
            </Tag>
            <span class="run-history__meta">
              {{ item.case_count }} 个用例 ·
              {{ formatEventTime(item.created_at) }}
            </span>
          </button>
        </div>
      </Card>

      <Card v-if="detail" :body-style="{ padding: '16px' }">
        <Descriptions bordered :column="3" size="small">
          <DescriptionsItem label="模块">{{ moduleName }}</DescriptionsItem>
          <DescriptionsItem label="架构">{{ detail.arch }}</DescriptionsItem>
          <DescriptionsItem label="环境">
            {{ envTypeLabel(detail.env_type) }}
          </DescriptionsItem>
          <DescriptionsItem label="状态">
            <Tag :color="statusColor(detail.status)">
              {{ statusLabel(detail.status) }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem v-if="detail.error_code" label="错误码">
            <Tag color="red">{{ detail.error_code }}</Tag>
          </DescriptionsItem>
          <DescriptionsItem
            v-if="detail.error_message"
            label="错误信息"
            :span="3"
          >
            <span style="color: hsl(var(--destructive))">{{
              detail.error_message
            }}</span>
          </DescriptionsItem>
          <DescriptionsItem label="节点 IP">
            <div class="flex flex-wrap gap-1">
              <Tag
                v-for="node in detail.nodes"
                :key="`${node.resource_code ?? ''}-${node.env_set_index ?? 0}-${node.node_index ?? 0}`"
                style="margin-bottom: 2px; cursor: pointer"
                @click="openNode(node.resource_id, node.env_type)"
              >
                {{ node.primary_ip || '-' }}
                <span class="node-role">({{ node.role }})</span>
                <template v-if="node.resource_id">
                  <ExternalLink class="ml-1 inline-block size-3" />
                </template>
              </Tag>
              <span
                v-if="!detail.nodes?.length"
                style="color: hsl(var(--muted-foreground))"
                >-</span
              >
            </div>
          </DescriptionsItem>
        </Descriptions>

        <!-- 执行过程（可收缩） -->
        <div v-if="detail.task_events?.length" class="task-events">
          <div class="task-events-header">
            <span class="task-events-title">执行过程</span>
            <Button
              size="small"
              type="link"
              @click="timelineExpanded = !timelineExpanded"
            >
              {{ timelineExpanded ? '收起' : '展开全部' }}
            </Button>
          </div>
          <div
            v-for="(ev, idx) in visibleTaskEvents"
            :key="idx"
            class="task-event"
          >
            <span class="task-event-time">{{
              formatEventTime(ev.created_at)
            }}</span>
            <Tag :color="eventColor(ev.level)" class="task-event-level">
              {{ ev.phase }}
            </Tag>
            <span
              class="task-event-msg"
              :class="{ 'task-event-error': ev.level === 'error' }"
            >
              {{ ev.message || '(无详细信息)' }}
            </span>
          </div>
        </div>
      </Card>

      <!-- 统计卡片 -->
      <Card v-if="detail" :body-style="{ padding: '16px' }">
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-label">总计</span>
            <span class="stat-value">{{ caseStats.total }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">通过</span>
            <span class="stat-value stat-pass">{{ caseStats.passed }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">失败</span>
            <span class="stat-value stat-fail">{{ caseStats.failed }}</span>
          </div>
          <div v-if="caseStats.skipped" class="stat-item">
            <span class="stat-label">跳过</span>
            <span class="stat-value stat-skip">{{ caseStats.skipped }}</span>
          </div>
          <div v-if="caseStats.toExecute" class="stat-item">
            <span class="stat-label">待执行</span>
            <span class="stat-value stat-skip">{{ caseStats.toExecute }}</span>
          </div>
          <div v-if="caseStats.notExecuted" class="stat-item">
            <span class="stat-label">未执行</span>
            <span class="stat-value stat-skip">{{
              caseStats.notExecuted
            }}</span>
          </div>
          <div v-if="caseStats.running" class="stat-item">
            <span class="stat-label">执行中</span>
            <span class="stat-value">{{ caseStats.running }}</span>
          </div>
          <div v-if="caseStats.error" class="stat-item">
            <span class="stat-label">异常</span>
            <span class="stat-value stat-fail">{{ caseStats.error }}</span>
          </div>
          <div v-if="caseStats.timeout" class="stat-item">
            <span class="stat-label">超时</span>
            <span class="stat-value stat-fail">{{ caseStats.timeout }}</span>
          </div>
        </div>
        <div v-if="isPkgcmd" class="stats-row">
          <div class="stat-item">
            <span class="stat-label">有用例的软件包个数</span>
            <span class="stat-value stat-pass">{{
              caseStats.foundPackages
            }}</span>
          </div>
          <div v-if="caseStats.no_case" class="stat-item">
            <span class="stat-label">没有用例的软件包个数</span>
            <span class="stat-value stat-skip">{{ caseStats.no_case }}</span>
          </div>
        </div>
      </Card>

      <div class="runjob-grid">
        <Card :body-style="{ padding: 0 }" class="runjob-left">
          <div class="px-4 pb-2 pt-3">
            <div class="text-base font-semibold">用例列表</div>
            <div class="mt-2 flex items-center gap-2">
              <Select v-model:value="caseFilter" style="width: 120px">
                <SelectOption value="all">全部</SelectOption>
                <SelectOption value="passed">通过</SelectOption>
                <SelectOption value="failed">失败</SelectOption>
                <SelectOption value="skipped">跳过</SelectOption>
                <SelectOption value="no_case">未找到用例</SelectOption>
                <SelectOption value="not_executed">未执行</SelectOption>
                <SelectOption value="error">异常</SelectOption>
                <SelectOption value="timeout">超时</SelectOption>
              </Select>
              <Input
                v-model:value="caseSearch"
                placeholder="搜索 suite/case"
                allow-clear
                style="flex: 1"
              />
            </div>
          </div>
          <Collapse :bordered="false" style="background: transparent">
            <CollapsePanel v-for="group in groupedCases" :key="group.suite">
              <template #header>
                <span class="font-semibold">{{ group.suite }}</span>
                <span
                  v-if="group.envTypes.size > 0 && !isUniform(group, 'no_case')"
                  style="
                    margin-left: 8px;
                    font-size: 12px;
                    color: hsl(var(--muted-foreground));
                  "
                >
                  {{
                    group.envTypes.size === 2
                      ? 'VM + 物理机'
                      : group.envTypes.has('physical')
                        ? '物理机'
                        : 'VM'
                  }}
                </span>
                <Tag
                  v-if="isUniform(group, 'no_case')"
                  color="volcano"
                  style="margin-left: 8px"
                >
                  未找到用例
                </Tag>
                <Tag
                  v-else-if="caseFilter !== 'all'"
                  :color="statusColor(caseFilter)"
                  style="margin-left: 8px"
                >
                  {{ statusLabel(caseFilter) }} {{ group.cases.length }}
                </Tag>
                <Tag
                  v-else-if="isUniform(group, 'not_executed')"
                  color="default"
                  style="margin-left: 8px"
                >
                  未执行
                </Tag>
                <Tag
                  v-else-if="isUniform(group, 'skipped')"
                  color="default"
                  style="margin-left: 8px"
                >
                  跳过
                </Tag>
                <Tag
                  v-else-if="isUniform(group, 'pending')"
                  color="default"
                  style="margin-left: 8px"
                >
                  待执行
                </Tag>
                <Tag
                  v-else-if="isInProgress(group)"
                  color="blue"
                  style="margin-left: 8px"
                >
                  执行中 {{ finishedCaseCount(group.cases) }}/{{
                    group.cases.length
                  }}
                </Tag>
                <Tag
                  v-else
                  :color="group.passed === group.cases.length ? 'green' : 'red'"
                  style="margin-left: 8px"
                >
                  通过 {{ group.passed }}/{{ group.cases.length }}
                </Tag>
              </template>
              <div
                v-for="cr in group.cases"
                :key="cr.id"
                class="flex items-center gap-2 py-1"
                style="cursor: pointer"
                @click="openCaseLog(cr.id)"
              >
                <Tag :color="statusColor(cr.status)" size="small">
                  {{ statusLabel(cr.status) }}
                </Tag>
                <span>{{ cr.case_name }}</span>
                <span
                  v-if="cr.exit_code !== null"
                  style="font-size: 12px; color: hsl(var(--muted-foreground))"
                >
                  exit={{ cr.exit_code }}
                </span>
              </div>
            </CollapsePanel>
          </Collapse>
        </Card>

        <Card :body-style="{ padding: 0 }" class="runjob-right">
          <!-- 执行结果: 仅 pkgmanage(内联报告) 和 kernel(日志+文件夹链接) -->
          <template v-if="isPkgmanage">
            <div class="px-4 pb-2 pt-3 text-base font-semibold">执行结果</div>
            <div
              v-for="art in reportArtifacts"
              :key="art.id"
              class="case-result-block"
            >
              <div class="case-result-header">
                <span class="case-result-name">{{ art.artifact_name }}</span>
              </div>
              <pre class="case-result-pre">{{
                art.content ?? '无报告内容'
              }}</pre>
            </div>
            <div
              v-if="reportArtifacts.length === 0"
              style="padding: 16px; color: hsl(var(--muted-foreground))"
            >
              无执行结果
            </div>
          </template>

          <!-- 日志: module_log + pkg_folder 统一展示 -->
          <div class="mugen-logs-section">
            <div
              class="px-4 pt-3 pb-2 text-sm font-semibold"
              style="color: hsl(var(--muted-foreground))"
            >
              日志
            </div>
            <div class="px-4 pb-3">
              <div class="flex flex-col gap-1">
                <Button
                  v-for="log in mugenLogs"
                  :key="log.id"
                  size="small"
                  type="link"
                  style="padding: 0; text-align: left"
                  @click="openLog(log.id)"
                >
                  {{ log.artifact_name }}
                  <span v-if="log.arch" class="log-arch">({{ log.arch }})</span>
                </Button>
                <Button
                  v-for="f in folderArtifacts"
                  :key="f.id"
                  size="small"
                  type="link"
                  style="padding: 0; text-align: left"
                  @click="openFolder(f.id)"
                >
                  {{ f.artifact_name }}/
                  <span v-if="f.arch" class="log-arch">({{ f.arch }})</span>
                </Button>
                <div
                  v-if="mugenLogs.length === 0 && folderArtifacts.length === 0"
                  class="text-center py-4"
                  style="color: hsl(var(--muted-foreground))"
                >
                  无日志
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.runjob-grid {
  display: grid;
  grid-template: 'left right' / 3fr 1fr;
  gap: 16px;
}

.runjob-left {
  grid-area: left;
}

.runjob-right {
  grid-area: right;
}

.run-history {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.run-history__item {
  display: grid;
  grid-template-columns: auto auto auto;
  gap: 4px 8px;
  align-items: center;
  min-width: 230px;
  padding: 9px 10px;
  color: inherit;
  text-align: left;
  background: hsl(var(--muted) / 35%);
  border: 1px solid hsl(var(--border));
  border-radius: 6px;
}

.run-history__item:hover,
.run-history__item:focus-visible {
  outline: none;
  border-color: hsl(var(--primary) / 55%);
}

.run-history__item--active {
  background: hsl(var(--primary) / 7%);
  border-color: hsl(var(--primary));
}

.run-history__marker {
  width: 7px;
  height: 7px;
  background: hsl(var(--primary));
  border-radius: 50%;
}

.run-history__title {
  font-weight: 600;
}

.run-history__meta {
  grid-column: 2 / -1;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

@media (max-width: 1200px) {
  .runjob-grid {
    grid-template-areas: 'left' 'right';
    grid-template-columns: 1fr;
  }
}

.stats-row {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
}

.stat-pass {
  color: hsl(var(--success));
}

.stat-fail {
  color: hsl(var(--destructive));
}

.stat-skip {
  color: hsl(var(--muted-foreground));
}

.log-arch {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.node-role {
  font-size: 10px;
  color: hsl(var(--muted-foreground));
}

.task-events {
  padding-top: 8px;
  margin-top: 12px;
  border-top: 1px solid hsl(var(--border));
}

.task-events-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.task-events-title {
  font-size: 14px;
  font-weight: 600;
}

.task-event {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
  line-height: 1.8;
}

.task-event-time {
  min-width: 160px;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
}

.task-event-level {
  min-width: 120px;
  text-align: center;
}

.task-event-msg {
  flex: 1;
  word-break: break-all;
}

.task-event-error {
  font-weight: 500;
  color: hsl(var(--destructive));
}

.case-result-block {
  padding: 12px 16px;
  border-top: 1px solid hsl(var(--border));
}

.case-result-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.case-result-name {
  font-size: 13px;
  font-weight: 500;
}

.case-result-pre {
  max-height: 200px;
  padding: 4px 8px;
  margin: 4px 0;
  overflow: auto;
  font-size: 11px;
  line-height: 1.5;
  color: hsl(var(--card-foreground));
  word-break: break-all;
  white-space: pre-wrap;
  background: hsl(var(--muted));
  border: 1px solid hsl(var(--border));
  border-radius: 4px;
}

.mugen-logs-section {
  border-top: 1px solid hsl(var(--border));
}
</style>
