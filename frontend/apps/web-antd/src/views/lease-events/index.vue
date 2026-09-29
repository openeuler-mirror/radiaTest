<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';
import type { Dayjs } from 'dayjs';

import type {
  LeaseEventListParams,
  LeaseEventRecord,
  TaskEventRecord,
} from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Eye } from '@vben/icons';

import {
  Button,
  Card,
  DatePicker,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import { getLeaseEventsApi, getVMEventsApi } from '#/api';

import { createLatestRequestGuard } from '../_shared/latest-request';
import ManagementFilterPanel from '../_shared/management-filter-panel.vue';
import { tablePagination } from '../_shared/table-pagination';
import TaskEventList from '../_shared/task-event-list.vue';

const { RangePicker } = DatePicker;
const leaseEventListRequest = createLatestRequestGuard();

type DateRange = [Dayjs, Dayjs] | undefined;

const loading = ref(false);
const events = ref<LeaseEventRecord[]>([]);
const eventPage = ref(1);
const eventTotal = ref(0);
const detailOpen = ref(false);
const selectedEvent = ref<LeaseEventRecord | null>(null);
const taskEventsOpen = ref(false);
const taskEventsLoading = ref(false);
const selectedResourceId = ref('');
const taskEvents = ref<TaskEventRecord[]>([]);

const filters = reactive({
  actorUsername: '',
  createdRange: undefined as DateRange,
  eventType: '',
  primaryIp: '',
  resourceCode: '',
  resourceType: '',
});

const columns: TableColumnsType<LeaseEventRecord> = [
  { dataIndex: 'created_at', fixed: 'left', title: '时间', width: 190 },
  { dataIndex: 'event_type', title: '事件类型', width: 150 },
  { dataIndex: 'resource_type', title: '资源类型', width: 110 },
  { dataIndex: 'primary_ip', title: 'OS IP', width: 150 },
  { dataIndex: 'resource_code', title: '资源编号', width: 210 },
  { dataIndex: 'actor_username', title: '操作者', width: 140 },
  { dataIndex: 'lease_id', title: '租约 ID', width: 260 },
  { key: 'detail', title: '详情摘要', width: 320 },
  { fixed: 'right', key: 'action', title: '', width: 180 },
];

const activeFilterCount = computed(() => {
  let count = 0;
  if (filters.eventType.trim()) count += 1;
  if (filters.actorUsername.trim()) count += 1;
  if (filters.resourceType) count += 1;
  if (filters.primaryIp.trim()) count += 1;
  if (filters.resourceCode.trim()) count += 1;
  if (filters.createdRange) count += 1;
  return count;
});

const selectedDetailJson = computed(() =>
  selectedEvent.value
    ? JSON.stringify(selectedEvent.value.detail, null, 2)
    : '',
);

function buildParams() {
  const params: LeaseEventListParams = { page: eventPage.value };
  const eventType = filters.eventType.trim();
  const actorUsername = filters.actorUsername.trim();
  const primaryIp = filters.primaryIp.trim();
  const resourceCode = filters.resourceCode.trim();
  if (eventType) params.event_type = eventType;
  if (actorUsername) params.actor_username = actorUsername;
  if (filters.resourceType) params.resource_type = filters.resourceType;
  if (primaryIp) params.primary_ip = primaryIp;
  if (resourceCode) params.resource_code = resourceCode;
  if (filters.createdRange) {
    params.started_at = filters.createdRange[0].toISOString();
    params.ended_at = filters.createdRange[1].toISOString();
  }
  return params;
}

async function loadEvents() {
  const request = leaseEventListRequest.begin();
  loading.value = true;
  try {
    const response = await getLeaseEventsApi(buildParams());
    request.commit(() => {
      events.value = response.items;
      eventTotal.value = response.total;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

function searchEvents() {
  eventPage.value = 1;
  void loadEvents();
}

function resetFilters() {
  filters.eventType = '';
  filters.actorUsername = '';
  filters.resourceType = '';
  filters.primaryIp = '';
  filters.resourceCode = '';
  filters.createdRange = undefined;
  searchEvents();
}

function changePage(pagination: TablePaginationConfig) {
  eventPage.value = pagination.current ?? 1;
  void loadEvents();
}

function openDetail(record: LeaseEventRecord) {
  selectedEvent.value = record;
  detailOpen.value = true;
}

async function loadTaskEvents() {
  if (!selectedResourceId.value) return;
  taskEventsLoading.value = true;
  try {
    taskEvents.value = await getVMEventsApi(selectedResourceId.value);
  } finally {
    taskEventsLoading.value = false;
  }
}

function openTaskEvents(record: LeaseEventRecord) {
  selectedResourceId.value = record.resource_id;
  taskEvents.value = [];
  taskEventsOpen.value = true;
  void loadTaskEvents();
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function displayValue(value: null | string) {
  return value || '-';
}

function actorLabel(record: LeaseEventRecord) {
  return record.actor_username || '系统';
}

function resourceTypeLabel(value: null | string) {
  if (value === 'PHYSICAL') return '物理机';
  if (value === 'VIRTUAL') return '虚拟机';
  return displayValue(value);
}

function detailSummary(detail: Record<string, unknown>) {
  const text = JSON.stringify(detail);
  return text.length > 160 ? `${text.slice(0, 160)}...` : text;
}

function asLeaseEventRecord(record: Record<string, unknown>) {
  return record as unknown as LeaseEventRecord;
}

onMounted(() => {
  void loadEvents();
});
</script>

<template>
  <Page title="租约日志">
    <div class="space-y-4">
      <ManagementFilterPanel
        :active-filter-count="activeFilterCount"
        :loading="loading"
        @reset="resetFilters"
        @search="searchEvents"
      >
        <div class="management-filter__field">
          <span class="management-filter__label">事件类型</span>
          <Input
            v-model:value="filters.eventType"
            allow-clear
            size="small"
            @press-enter="searchEvents"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">操作者</span>
          <Input
            v-model:value="filters.actorUsername"
            allow-clear
            size="small"
            @press-enter="searchEvents"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">资源类型</span>
          <Select
            v-model:value="filters.resourceType"
            :options="[
              { label: '全部', value: '' },
              { label: '物理机', value: 'PHYSICAL' },
              { label: '虚拟机', value: 'VIRTUAL' },
            ]"
            size="small"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">OS IP</span>
          <Input
            v-model:value="filters.primaryIp"
            allow-clear
            size="small"
            @press-enter="searchEvents"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">资源编号</span>
          <Input
            v-model:value="filters.resourceCode"
            allow-clear
            size="small"
            @press-enter="searchEvents"
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
            <span>租约日志</span>
            <Tag>{{ eventTotal }}</Tag>
          </Space>
        </template>
        <Table
          :columns="columns"
          :data-source="events"
          :loading="loading"
          :pagination="tablePagination(eventPage, eventTotal)"
          :scroll="{ x: 1710 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'created_at'">
              {{ formatTime(record.created_at) }}
            </template>
            <template v-else-if="column.dataIndex === 'actor_username'">
              {{ actorLabel(asLeaseEventRecord(record)) }}
            </template>
            <template v-else-if="column.dataIndex === 'resource_type'">
              {{ resourceTypeLabel(record.resource_type) }}
            </template>
            <template v-else-if="column.dataIndex === 'resource_code'">
              {{ displayValue(record.resource_code) }}
            </template>
            <template v-else-if="column.key === 'detail'">
              {{ detailSummary(record.detail) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Space :size="4">
                <Button
                  size="small"
                  type="link"
                  @click="openDetail(asLeaseEventRecord(record))"
                >
                  <template #icon><Eye class="size-4" /></template>
                  详情
                </Button>
                <Button
                  v-if="record.resource_type === 'VIRTUAL'"
                  size="small"
                  type="link"
                  @click="openTaskEvents(asLeaseEventRecord(record))"
                >
                  任务事件
                </Button>
              </Space>
            </template>
            <template v-else>{{ displayValue(text) }}</template>
          </template>
        </Table>
      </Card>
    </div>

    <Modal
      v-model:open="detailOpen"
      title="租约日志详情"
      :footer="null"
      width="720px"
    >
      <pre class="max-h-[60vh] overflow-auto whitespace-pre-wrap break-all">{{
        selectedDetailJson
      }}</pre>
    </Modal>

    <Modal
      v-model:open="taskEventsOpen"
      title="VM 销毁任务事件"
      :footer="null"
      width="800px"
    >
      <TaskEventList
        :events="taskEvents"
        :loading="taskEventsLoading"
        @refresh="loadTaskEvents"
      />
    </Modal>
  </Page>
</template>
