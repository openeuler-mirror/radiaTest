<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';
import type { Dayjs } from 'dayjs';

import type { AuditLogListParams, AuditLogRecord } from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Eye } from '@vben/icons';

import {
  Button,
  Card,
  DatePicker,
  Input,
  Modal,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import { getAuditLogsApi } from '#/api';

import { createLatestRequestGuard } from '../_shared/latest-request';
import ManagementFilterPanel from '../_shared/management-filter-panel.vue';
import { tablePagination } from '../_shared/table-pagination';

const { RangePicker } = DatePicker;
const auditListRequest = createLatestRequestGuard();

type DateRange = [Dayjs, Dayjs] | undefined;

const loading = ref(false);
const logs = ref<AuditLogRecord[]>([]);
const logPage = ref(1);
const logTotal = ref(0);
const detailOpen = ref(false);
const selectedLog = ref<AuditLogRecord | null>(null);

const filters = reactive({
  action: '',
  actor_username: '',
  createdRange: undefined as DateRange,
  target_type: '',
});

const columns: TableColumnsType<AuditLogRecord> = [
  {
    dataIndex: 'created_at',
    fixed: 'left',
    title: '时间',
    width: 190,
  },
  {
    dataIndex: 'actor_username',
    title: '操作者',
    width: 140,
  },
  {
    dataIndex: 'action',
    title: '操作类型',
    width: 190,
  },
  {
    dataIndex: 'target_type',
    title: '目标类型',
    width: 130,
  },
  {
    dataIndex: 'target_id',
    title: '目标 ID',
    width: 240,
  },
  {
    key: 'detail',
    title: '详情摘要',
    width: 320,
  },
  {
    fixed: 'right',
    key: 'action',
    title: '',
    width: 90,
  },
];

const activeFilterCount = computed(() => {
  let count = 0;
  if (filters.action.trim()) count += 1;
  if (filters.actor_username.trim()) count += 1;
  if (filters.target_type.trim()) count += 1;
  if (filters.createdRange) count += 1;
  return count;
});

const selectedDetailJson = computed(() =>
  selectedLog.value ? JSON.stringify(selectedLog.value.detail, null, 2) : '',
);

function buildParams() {
  const params: AuditLogListParams = { page: logPage.value };
  const action = filters.action.trim();
  const actorUsername = filters.actor_username.trim();
  const targetType = filters.target_type.trim();
  if (action) params.action = action;
  if (actorUsername) params.actor_username = actorUsername;
  if (targetType) params.target_type = targetType;
  if (filters.createdRange) {
    params.started_at = filters.createdRange[0].toISOString();
    params.ended_at = filters.createdRange[1].toISOString();
  }
  return params;
}

async function loadLogs() {
  const request = auditListRequest.begin();
  loading.value = true;
  try {
    const response = await getAuditLogsApi(buildParams());
    request.commit(() => {
      logs.value = response.items;
      logTotal.value = response.total;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

function searchLogs() {
  logPage.value = 1;
  void loadLogs();
}

function resetFilters() {
  filters.action = '';
  filters.actor_username = '';
  filters.target_type = '';
  filters.createdRange = undefined;
  searchLogs();
}

function changePage(pagination: TablePaginationConfig) {
  logPage.value = pagination.current ?? 1;
  void loadLogs();
}

function openDetail(record: AuditLogRecord) {
  selectedLog.value = record;
  detailOpen.value = true;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function displayValue(value: null | string) {
  return value || '-';
}

function detailSummary(detail: Record<string, unknown>) {
  const text = JSON.stringify(detail);
  return text.length > 160 ? `${text.slice(0, 160)}...` : text;
}

function asAuditLogRecord(record: Record<string, unknown>) {
  return record as unknown as AuditLogRecord;
}

onMounted(() => {
  void loadLogs();
});
</script>

<template>
  <Page title="审计日志">
    <div class="space-y-4">
      <ManagementFilterPanel
        :active-filter-count="activeFilterCount"
        :loading="loading"
        @reset="resetFilters"
        @search="searchLogs"
      >
        <div class="management-filter__field">
          <span class="management-filter__label">操作类型</span>
          <Input
            v-model:value="filters.action"
            allow-clear
            size="small"
            @press-enter="searchLogs"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">操作者</span>
          <Input
            v-model:value="filters.actor_username"
            allow-clear
            size="small"
            @press-enter="searchLogs"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">目标类型</span>
          <Input
            v-model:value="filters.target_type"
            allow-clear
            size="small"
            @press-enter="searchLogs"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">时间范围</span>
          <RangePicker
            v-model:value="filters.createdRange"
            show-time
            size="small"
            class="w-full"
          />
        </div>
      </ManagementFilterPanel>

      <Card :body-style="{ padding: 0 }">
        <template #title>
          <Space>
            <span>审计日志</span>
            <Tag>{{ logTotal }}</Tag>
          </Space>
        </template>
        <Table
          :columns="columns"
          :data-source="logs"
          :loading="loading"
          :pagination="tablePagination(logPage, logTotal)"
          :scroll="{ x: 1280 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'created_at'">
              {{ formatTime(record.created_at) }}
            </template>
            <template v-else-if="column.dataIndex === 'actor_username'">
              {{ displayValue(record.actor_username) }}
            </template>
            <template v-else-if="column.dataIndex === 'target_id'">
              {{ displayValue(record.target_id) }}
            </template>
            <template v-else-if="column.key === 'detail'">
              {{ detailSummary(record.detail) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Button
                size="small"
                type="link"
                @click="openDetail(asAuditLogRecord(record))"
              >
                <template #icon>
                  <Eye class="size-4" />
                </template>
                详情
              </Button>
            </template>
            <template v-else>
              {{ displayValue(text) }}
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <Modal
      v-model:open="detailOpen"
      :footer="null"
      destroy-on-close
      title="审计详情"
      width="720px"
    >
      <pre class="management-json">{{ selectedDetailJson }}</pre>
    </Modal>
  </Page>
</template>
