<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type {
  MugenCaseRecord,
  TaskEventRecord,
  TestEnvType,
  UserRole,
} from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { List, RotateCw } from '@vben/icons';
import { useUserStore } from '@vben/stores';

import {
  Button,
  Card,
  Drawer,
  Input,
  message,
  Modal,
  Select,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  getTestCasesApi,
  getTestCaseSyncEventsApi,
  syncTestCasesApi,
} from '#/api';

import { createLatestRequestGuard } from '../_shared/latest-request';
import ManagementFilterPanel from '../_shared/management-filter-panel.vue';
import { tablePagination } from '../_shared/table-pagination';
import TaskEventList from '../_shared/task-event-list.vue';
import { isCaseSelectable } from '../test-jobs/test-job-view';

const loading = ref(false);
const caseListRequest = createLatestRequestGuard();
const syncing = ref(false);
const eventsLoading = ref(false);
const eventsOpen = ref(false);
const cases = ref<MugenCaseRecord[]>([]);
const casePage = ref(1);
const caseTotal = ref(0);
const syncEvents = ref<TaskEventRecord[]>([]);
const currentCommit = ref('');
const userStore = useUserStore();

const filters = reactive({
  caseName: '',
  envType: '' as '' | TestEnvType,
  suiteName: '',
});

const activeFilterCount = computed(
  () =>
    [filters.caseName, filters.envType, filters.suiteName].filter((value) =>
      value.trim(),
    ).length,
);

const currentRole = computed(
  () => userStore.userInfo?.roles?.[0] as undefined | UserRole,
);
const isAdmin = computed(() => currentRole.value === 'ADMIN');

const columns: TableColumnsType<MugenCaseRecord> = [
  { dataIndex: 'suite_name', fixed: 'left', title: 'Suite', width: 240 },
  { dataIndex: 'case_name', ellipsis: true, title: 'Case', width: 320 },
  { dataIndex: 'env_type', title: '环境类型', width: 110 },
  { dataIndex: 'node_num', title: '节点', width: 80 },
  { dataIndex: 'add_disk_num', title: '额外数据盘', width: 110 },
  { dataIndex: 'add_nic_num', title: '额外网卡', width: 100 },
  { key: 'selectable', title: '可选状态', width: 100 },
  { dataIndex: 'commit_sha', ellipsis: true, title: 'Commit', width: 180 },
  { dataIndex: 'synced_at', title: '同步时间', width: 180 },
];

const envTypeOptions = [
  { label: '全部', value: '' },
  { label: 'VM', value: 'vm' },
  { label: '物理机', value: 'physical' },
  { label: '未知', value: 'unknown' },
];

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function envTypeLabel(value: TestEnvType) {
  const labels: Record<TestEnvType, string> = {
    physical: '物理机',
    unknown: '未知',
    vm: 'VM',
  };
  return labels[value];
}

function recordIsSelectable(record: Record<string, unknown>) {
  return isCaseSelectable(record as unknown as MugenCaseRecord);
}

async function loadCases() {
  const request = caseListRequest.begin();
  const params = {
    case: filters.caseName.trim() || undefined,
    env_type: filters.envType || undefined,
    page: casePage.value,
    suite: filters.suiteName.trim() || undefined,
  };
  const hasFilters = Boolean(params.case || params.env_type || params.suite);
  loading.value = true;
  try {
    const response = await getTestCasesApi(params);
    const rows = response.items;
    let commitSha = '';
    if (rows[0]) {
      commitSha = rows[0].commit_sha;
    } else if (hasFilters) {
      const indexResponse = await getTestCasesApi();
      commitSha = indexResponse.items[0]?.commit_sha ?? '';
    }
    request.commit(() => {
      cases.value = rows;
      caseTotal.value = response.total;
      currentCommit.value = commitSha;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

function searchCases() {
  casePage.value = 1;
  void loadCases();
}

function resetFilters() {
  filters.caseName = '';
  filters.envType = '';
  filters.suiteName = '';
  searchCases();
}

function changePage(pagination: TablePaginationConfig) {
  casePage.value = pagination.current ?? 1;
  void loadCases();
}

async function loadSyncEvents() {
  if (!isAdmin.value) return;
  eventsLoading.value = true;
  try {
    syncEvents.value = await getTestCaseSyncEventsApi();
  } finally {
    eventsLoading.value = false;
  }
}

function openSyncEvents() {
  eventsOpen.value = true;
  void loadSyncEvents();
}

function confirmSync() {
  Modal.confirm({
    content: '同步会用 Mugen 仓库当前内容替换已有用例索引。',
    okText: '开始同步',
    onOk: submitSync,
    title: '同步 Mugen 用例',
  });
}

async function submitSync() {
  syncing.value = true;
  try {
    await syncTestCasesApi();
    message.success('同步任务已进入队列');
    eventsOpen.value = true;
    await loadSyncEvents();
  } finally {
    syncing.value = false;
  }
}

onMounted(() => {
  void loadCases();
});
</script>

<template>
  <Page title="测试用例">
    <div class="space-y-4">
      <ManagementFilterPanel
        :active-filter-count="activeFilterCount"
        :loading="loading"
        @reset="resetFilters"
        @search="searchCases"
      >
        <div class="management-filter__field">
          <span class="management-filter__label">Suite</span>
          <Input
            v-model:value="filters.suiteName"
            allow-clear
            size="small"
            @press-enter="searchCases"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">Case</span>
          <Input
            v-model:value="filters.caseName"
            allow-clear
            size="small"
            @press-enter="searchCases"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">环境类型</span>
          <Select
            v-model:value="filters.envType"
            :options="envTypeOptions"
            class="w-full"
            size="small"
          />
        </div>
      </ManagementFilterPanel>

      <Card class="management-table-card" :body-style="{ padding: 0 }">
        <div class="management-toolbar management-toolbar--table">
          <div class="management-toolbar__group">
            <span>用例索引</span>
            <Tag>{{ caseTotal }} 条</Tag>
            <Tag v-if="currentCommit" color="blue">
              {{ currentCommit.slice(0, 12) }}
            </Tag>
          </div>
          <div
            v-if="isAdmin"
            class="management-toolbar__actions management-toolbar__group"
          >
            <Button size="small" @click="openSyncEvents">
              <template #icon><List class="size-4" /></template>
              同步记录
            </Button>
            <Button
              :loading="syncing"
              size="small"
              type="primary"
              @click="confirmSync"
            >
              <template #icon><RotateCw class="size-4" /></template>
              同步 Mugen
            </Button>
          </div>
        </div>
        <Table
          :columns="columns"
          :data-source="cases"
          :loading="loading"
          :pagination="tablePagination(casePage, caseTotal)"
          :scroll="{ x: 1420 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'env_type'">
              <Tag :color="record.env_type === 'vm' ? 'blue' : 'default'">
                {{ envTypeLabel(record.env_type) }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'synced_at'">
              {{ formatTime(record.synced_at) }}
            </template>
            <template v-else-if="column.key === 'selectable'">
              <Tag :color="recordIsSelectable(record) ? 'green' : 'default'">
                {{ recordIsSelectable(record) ? '可选' : '不可选' }}
              </Tag>
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <Drawer
      v-model:open="eventsOpen"
      :destroy-on-close="true"
      placement="right"
      title="Mugen 同步记录"
      width="min(720px, calc(100vw - 16px))"
    >
      <TaskEventList
        :events="syncEvents"
        :loading="eventsLoading"
        @refresh="loadSyncEvents"
      />
    </Drawer>
  </Page>
</template>
