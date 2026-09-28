<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  CompareRecord,
  CompareResultRecord,
  MilestoneRecord,
  VersionRecord,
} from '#/api';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  message,
  Select,
  SelectOption,
  Table,
  TabPane,
  Tabs,
  Tag,
} from 'ant-design-vue';

import {
  downloadCompareExportApi,
  getCompareApi,
  listCompareResultsApi,
  listVersionMilestonesApi,
  listVersionsApi,
  triggerCompareApi,
} from '#/api';
import { parseAPIError } from '#/api/api-error';

type Kind = 'binary' | 'isomer' | 'repeat' | 'source';

const KIND_OPTIONS: { label: string; value: Kind }[] = [
  { value: 'binary', label: '二进制' },
  { value: 'source', label: '源码' },
  { value: 'isomer', label: '同名异构' },
  { value: 'repeat', label: '重复包' },
];
const KIND_STATUS: Record<string, string[]> = {
  binary: ['ADD', 'DEL', 'VER_UP', 'VER_DOWN', 'REL_UP', 'REL_DOWN'],
  source: ['ADD', 'DEL', 'VER_UP', 'VER_DOWN', 'REL_UP', 'REL_DOWN'],
  isomer: ['SAME', 'DIFFERENT', 'LACK'],
  repeat: ['REPEAT'],
};
const STATUS_LABEL: Record<string, string> = {
  ADD: '新增',
  DEL: '删除',
  VER_UP: '版本升级',
  VER_DOWN: '版本降级',
  REL_UP: 'release升级',
  REL_DOWN: 'release降级',
  SAME: '一致',
  DIFFERENT: '不同',
  LACK: '缺失',
  REPEAT: '重复包',
};
const STATUS_COLOR: Record<string, string> = {
  ADD: 'green',
  DEL: 'red',
  VER_UP: 'blue',
  VER_DOWN: 'orange',
  REL_UP: 'blue',
  REL_DOWN: 'red',
  SAME: 'default',
  DIFFERENT: 'orange',
  LACK: 'default',
  REPEAT: 'orange',
};

const route = useRoute();
const router = useRouter();
const versionId = route.params.id as string;
const milestoneId = route.params.milestoneId as string;

const version = ref<null | VersionRecord>(null);
const milestone = ref<MilestoneRecord | null>(null);
const milestones = ref<MilestoneRecord[]>([]);
const activeTab = ref('compare');

const baseId = ref<string | undefined>(undefined);
const triggering = ref(false);

const compare = ref<CompareRecord | null>(null);
const results = ref<CompareResultRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 50;
const resultsLoading = ref(false);

const filterKind = ref<Kind>('binary');
const filterRepo = ref('all');
const filterArch = ref('all');
const filterStatus = ref<string[]>([...(KIND_STATUS.binary ?? [])]);

let pollTimer: ReturnType<typeof setInterval> | undefined;

const otherMilestones = computed(() =>
  milestones.value.filter((m) => m.id !== milestoneId),
);

const columns = computed<TableColumnsType>(() => {
  const cols: TableColumnsType = [
    {
      key: 'pkg',
      title: filterKind.value === 'isomer' ? '包名' : '软件包',
      dataIndex: 'pkg_name',
    },
    { key: 'status', title: '变更', dataIndex: 'status', width: 130 },
    { key: 'from', title: '基准', dataIndex: 'rpm_base', ellipsis: true },
    { key: 'to', title: '目标', dataIndex: 'rpm_target', ellipsis: true },
    { key: 'arch', title: '架构', dataIndex: 'arch', width: 110 },
    { key: 'repo', title: '仓库', dataIndex: 'repo_path', width: 120 },
  ];
  return cols;
});

const summaryCounts = computed(() => {
  const out: { count: number; label: string }[] = [];
  const summary = compare.value?.summary;
  if (!summary) return out;
  const kindMap = summary[filterKind.value];
  if (kindMap) {
    for (const [status, count] of Object.entries(kindMap)) {
      out.push({ label: STATUS_LABEL[status] ?? status, count });
    }
  }
  return out;
});

function archLabelOf(r: { arch?: null | string }) {
  if (filterKind.value === 'source') return 'src';
  if (filterKind.value === 'isomer') return 'x86/arm';
  return r.arch ?? '—';
}

function repoLabelOf(r: { repo_path?: null | string }) {
  return r.repo_path === 'EPOL/main' ? 'EPOL' : r.repo_path;
}

async function loadContext() {
  try {
    const list = await listVersionsApi();
    version.value = list.items.find((v) => v.id === versionId) ?? null;
    milestones.value = await listVersionMilestonesApi(versionId);
    milestone.value =
      milestones.value.find((m) => m.id === milestoneId) ?? null;
    if (!milestone.value) {
      message.warning('里程碑不存在');
      return;
    }
    baseId.value = milestone.value.compare_base_milestone_id ?? '';
    const latest = milestone.value.latest_compare;
    if (latest) {
      compare.value = {
        id: latest.id,
        milestone_id: milestoneId,
        base_milestone_id: '',
        status: latest.status as CompareRecord['status'],
        total_changed: latest.total_changed,
        triggered_by: '',
        triggered_at: '',
        created_at: '',
      };
      if (latest.status === 'succeeded') {
        void loadResults();
      }
    }
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '加载轮次信息失败');
  }
}

async function loadResults() {
  if (!compare.value) return;
  resultsLoading.value = true;
  try {
    const resp = await listCompareResultsApi(compare.value.id, {
      page: page.value,
      kind: filterKind.value,
      repo_path: filterRepo.value === 'all' ? undefined : filterRepo.value,
      arch: filterArch.value === 'all' ? undefined : filterArch.value,
      status: filterStatus.value.length > 0 ? filterStatus.value : undefined,
    });
    results.value = resp.items;
    total.value = resp.total;
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '加载比对结果失败');
  } finally {
    resultsLoading.value = false;
  }
}

function onFilter() {
  page.value = 1;
  if (compare.value?.status === 'succeeded') {
    void loadResults();
  }
}

function onChangeKind(kind: Kind) {
  filterKind.value = kind;
  filterStatus.value = [...(KIND_STATUS[kind] ?? [])];
  onFilter();
}

function toggleStatus(status: string) {
  const i = filterStatus.value.indexOf(status);
  if (i === -1) {
    filterStatus.value.push(status);
  } else {
    filterStatus.value.splice(i, 1);
  }
  onFilter();
}

async function trigger() {
  if (!baseId.value) {
    message.warning('请选择比对基准');
    return;
  }
  triggering.value = true;
  try {
    const record = await triggerCompareApi(milestoneId, baseId.value);
    compare.value = record;
    filterKind.value = 'binary';
    filterRepo.value = 'all';
    filterArch.value = 'all';
    filterStatus.value = [...(KIND_STATUS.binary ?? [])];
    message.success('比对任务已创建，执行中');
    void pollCompare();
    pollTimer = setInterval(() => void pollCompare(), 2500);
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '触发比对失败');
  } finally {
    triggering.value = false;
  }
}

async function pollCompare() {
  if (!compare.value) return;
  try {
    const cur = await getCompareApi(compare.value.id);
    compare.value = cur;
    if (cur.status === 'succeeded') {
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = undefined;
      page.value = 1;
      void loadResults();
    } else if (cur.status === 'failed') {
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = undefined;
      message.error(`比对失败：${cur.error_msg ?? '未知原因'}`);
    }
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '查询比对状态失败');
  }
}

async function downloadCsv() {
  // 拉取当前筛选全集（非仅当前页）
  const compareId = compare.value?.id;
  if (compareId === undefined) {
    message.error('轮次数据未加载，无法导出');
    return;
  }
  const all: CompareResultRecord[] = [];
  for (let p = 1; all.length < total.value || p === 1; p += 1) {
    const resp = await listCompareResultsApi(compareId, {
      page: p,

      kind: filterKind.value,
      repo_path: filterRepo.value === 'all' ? undefined : filterRepo.value,
      arch: filterArch.value === 'all' ? undefined : filterArch.value,
      status: filterStatus.value.length > 0 ? filterStatus.value : undefined,
    });
    all.push(...resp.items);
    if (resp.items.length === 0 || all.length >= resp.total || p > 200) break;
  }
  const rows = all;
  if (rows.length === 0) {
    message.info('当前筛选无数据可导出');
    return;
  }
  const head = ['仓库', '架构', '变更', '软件包', '基准', '目标'];
  const lines = [head.join(',')];
  for (const r of rows) {
    lines.push(
      [
        repoLabelOf(r),
        archLabelOf(r),
        r.status,
        r.pkg_name,
        r.rpm_base ?? '',
        r.rpm_target ?? '',
      ]
        .map((v) => `"${String(v).replaceAll('"', '""')}"`)
        .join(','),
    );
  }
  const blob = new Blob([`\uFEFF${lines.join('\r\n')}`], {
    type: 'text/csv;charset=utf-8',
  });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `rc-compare-${milestone.value?.name ?? ''}-当前筛选.csv`;
  a.click();
}

async function exportZip() {
  if (!compare.value) return;
  try {
    const { blob, filename } = await downloadCompareExportApi(compare.value.id);
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    message.success('交付物 zip 已导出');
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '导出失败');
  }
}

function compareLabel(cur: CompareRecord | null) {
  if (!cur) return '';

  if (cur.status === 'succeeded')
    return `比对完成 · ${cur.total_changed ?? 0} 项变更`;
  if (cur.status === 'failed') return '比对失败';
  return '比对执行中';
}

onMounted(() => {
  void loadContext();
});

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <Page title="轮次测试控制台" :content-style="{ padding: '16px' }">
    <div class="mb-3">
      <a
        class="text-sm"
        href="javascript:void(0)"
        @click="router.push(`/versions/${versionId}`)"
      >
        返回到版本里程碑列表
      </a>
    </div>

    <Card :bordered="false" class="mb-4">
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="m-0">
              {{ version?.name }} ·
              <span class="font-mono">{{ milestone?.name }}</span>
            </h2>
            <Tag v-if="version?.version_type" color="blue">
              {{ version.version_type }}
            </Tag>
            <Tag color="green">进行中</Tag>
          </div>
          <div class="mt-1 text-sm text-gray-500">
            起止 {{ milestone?.start_time ?? '—' }} ~
            {{ milestone?.end_time ?? '—' }} · kernel
            {{ milestone?.kernel_variant ?? '—' }} · 比对基准
            {{ milestone?.compare_base_name ?? '—' }}
          </div>
        </div>
      </div>
    </Card>

    <Tabs v-model:active-key="activeTab">
      <TabPane key="compare" tab="软件包比对">
        <Card :bordered="false">
          <template #title>软件包比对</template>

          <div class="mb-4 flex flex-wrap items-end gap-4">
            <div>
              <div class="mb-1 text-xs text-gray-500">当前轮次</div>
              <div class="font-mono">{{ milestone?.name }}</div>
            </div>
            <div>
              <div class="mb-1 text-xs text-gray-500">比对基准</div>
              <Select
                v-model:value="baseId"
                style="width: 220px"
                placeholder="选择基准轮次"
              >
                <SelectOption
                  v-for="m in otherMilestones"
                  :key="m.id"
                  :value="m.id"
                >
                  {{ m.name }}
                </SelectOption>
              </Select>
            </div>
            <Button
              type="primary"
              :loading="triggering"
              :disabled="
                compare?.status === 'running' || compare?.status === 'pending'
              "
              @click="trigger"
            >
              开始比对（异步任务）
            </Button>
            <Tag
              v-if="compare"
              :color="
                compare.status === 'succeeded'
                  ? 'green'
                  : compare.status === 'failed'
                    ? 'red'
                    : 'orange'
              "
            >
              {{ compareLabel(compare) }}
            </Tag>
          </div>

          <template v-if="compare?.status === 'succeeded'">
            <div class="mb-3 flex gap-2">
              <Button size="small" @click="downloadCsv">
                导出 CSV (当前筛选)
              </Button>
              <Button size="small" @click="exportZip">
                导出交付 ZIP（7 xls）
              </Button>
            </div>
            <div class="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div
                v-for="item in summaryCounts"
                :key="item.label"
                class="rounded border border-gray-200 px-3 py-2"
              >
                <div class="text-xl font-semibold">{{ item.count }}</div>
                <div class="text-xs text-gray-500">{{ item.label }}</div>
              </div>
            </div>

            <div class="mb-3 flex flex-wrap items-center gap-2">
              <span class="text-xs text-gray-400">比对内容：</span>
              <Button
                v-for="o in KIND_OPTIONS"
                :key="o.value"
                size="small"
                :type="filterKind === o.value ? 'primary' : 'default'"
                @click="onChangeKind(o.value)"
              >
                {{ o.label }}
              </Button>
              <span class="ml-2 text-xs text-gray-400">仓库：</span>
              <Button
                v-for="r in ['all', 'everything', 'EPOL/main']"
                :key="r"
                size="small"
                :type="filterRepo === r ? 'primary' : 'default'"
                @click="
                  () => {
                    filterRepo = r;
                    onFilter();
                  }
                "
              >
                {{ r === 'all' ? '全部' : r === 'EPOL/main' ? 'EPOL' : r }}
              </Button>
              <span class="ml-2 text-xs text-gray-400">架构：</span>
              <Button
                v-for="a in ['all', 'x86_64', 'aarch64']"
                :key="a"
                size="small"
                :type="filterArch === a ? 'primary' : 'default'"
                @click="
                  () => {
                    filterArch = a;
                    onFilter();
                  }
                "
              >
                {{ a === 'all' ? '全部' : a }}
              </Button>
              <span class="ml-2 text-xs text-gray-400">变更：</span>
              <Button
                v-for="s in KIND_STATUS[filterKind]"
                :key="s"
                size="small"
                :type="filterStatus.includes(s) ? 'primary' : 'default'"
                @click="toggleStatus(s)"
              >
                {{ STATUS_LABEL[s] }}
              </Button>
            </div>

            <Table
              :columns="columns"
              :data-source="results"
              :loading="resultsLoading"
              row-key="id"
              size="small"
              :pagination="{
                current: page,
                pageSize,
                total,
                showSizeChanger: false,
                onChange: (p: number) => {
                  page = p;
                  void loadResults();
                },
              }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <Tag :color="STATUS_COLOR[record.status] ?? 'default'">
                    {{ STATUS_LABEL[record.status] ?? record.status }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'arch'">
                  {{ archLabelOf(record) }}
                </template>
                <template v-else-if="column.key === 'repo'">
                  {{ repoLabelOf(record) }}
                </template>
              </template>
            </Table>
          </template>

          <a-empty
            v-else-if="!compare"
            description="点击「开始比对」产出本轮测试输入（变更包清单）"
          />
        </Card>
      </TabPane>

      <TabPane key="progress" tab="测试进展">
        <Card :bordered="false">
          <div class="py-16 text-center text-gray-400">
            <div class="text-2xl">T</div>
            <div class="mt-2">本轮尚无测试活动</div>
            <div class="text-xs">
              「测试进展」汇总引例测试 /
              模块型测试的执行状态，由后续流水线执行回填
            </div>
          </div>
        </Card>
      </TabPane>

      <TabPane key="cases" tab="用例筛选">
        <Card :bordered="false">
          <div class="py-16 text-center text-gray-400">
            <div class="text-2xl">C</div>
            <div class="mt-2">按比对结果筛选用例（下一期）</div>
            <div class="text-xs">
              根据比对变更包匹配 mugen 用例（suite_name == 包名，systemd 服务转
              oe_test_service_*）并触发流水线，结果回填「测试进展」
            </div>
            <Button class="mt-4" disabled>筛选用例并触发测试（下一期）</Button>
          </div>
        </Card>
      </TabPane>

      <TabPane key="modules" tab="测试模块">
        <Card :bordered="false">
          <div class="py-16 text-center text-gray-400">
            <div class="text-2xl">M</div>
            <div class="mt-2">模块型测试（预留）</div>
            <div class="text-xs">
              与 update 测试一致：需要编写/配置测试模块（docker / kernel /
              pkgcmd / pkgserver）而非直接跑单用例的测试类型，登记到本轮执行
            </div>
          </div>
        </Card>
      </TabPane>
    </Tabs>
  </Page>
</template>
