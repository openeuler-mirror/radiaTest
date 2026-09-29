<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type {
  TicketCreatePayload,
  TicketListParams,
  TicketMatchMode,
  TicketPriority,
  TicketRecord,
  TicketStatus,
  TicketType,
} from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Eye, Plus, RotateCw } from '@vben/icons';

import {
  Button,
  Card,
  Input,
  InputNumber,
  message,
  RadioButton,
  RadioGroup,
  Select,
  Table,
  Tag,
  Tooltip,
} from 'ant-design-vue';

import { createTicketApi, getTicketsApi } from '#/api';

import { createLatestRequestGuard } from '../_shared/latest-request';
import ManagementFilterPanel from '../_shared/management-filter-panel.vue';
import { tablePagination } from '../_shared/table-pagination';
import TicketContentModal from './ticket-content-modal.vue';
import {
  formatTicketTime,
  ticketPriorityLabel,
  ticketPriorityOptions,
  ticketStatusColor,
  ticketStatusLabel,
  ticketStatusOptions,
  userDisplayName,
} from './ticket-view';

const router = useRouter();
const ticketListRequest = createLatestRequestGuard();
const loading = ref(false);
const creating = ref(false);
const createOpen = ref(false);
const tickets = ref<TicketRecord[]>([]);
const ticketPage = ref(1);
const ticketTotal = ref(0);
const matchMode = ref<TicketMatchMode>('and');
const filters = reactive({
  assignee: '',
  priority: '' as '' | 'UNSET' | TicketPriority,
  status: '' as '' | TicketStatus,
  submitter: '',
  ticketId: undefined as number | undefined,
  ticketType: '' as '' | TicketType,
  title: '',
});

const activeFilterCount = computed(
  () =>
    [
      filters.ticketId,
      filters.submitter.trim(),
      filters.title.trim(),
      filters.ticketType,
      filters.status,
      filters.priority,
      filters.assignee.trim(),
    ].filter(Boolean).length,
);

const columns: TableColumnsType<TicketRecord> = [
  { dataIndex: 'id', fixed: 'left', title: '序号', width: 90 },
  { key: 'submitter', title: '提出人', width: 160 },
  { dataIndex: 'ticket_type', title: '类型', width: 90 },
  { dataIndex: 'title', ellipsis: true, title: '标题', width: 320 },
  { dataIndex: 'status', title: '状态', width: 110 },
  { dataIndex: 'priority', title: '优先级', width: 100 },
  { key: 'assignee', title: '责任人', width: 160 },
  {
    dataIndex: 'planned_completion_at',
    title: '计划完成时间',
    width: 190,
  },
  { fixed: 'right', key: 'action', title: '', width: 90 },
];

function buildParams(): TicketListParams {
  const params: TicketListParams = {
    match: matchMode.value,
    page: ticketPage.value,
  };
  if (filters.ticketId) params.ticket_id = filters.ticketId;
  if (filters.submitter.trim()) params.submitter = filters.submitter.trim();
  if (filters.title.trim()) params.title = filters.title.trim();
  if (filters.ticketType) params.ticket_type = filters.ticketType;
  if (filters.status) params.status = filters.status;
  if (filters.priority) params.priority = filters.priority;
  if (filters.assignee.trim()) params.assignee = filters.assignee.trim();
  return params;
}

async function loadTickets() {
  const request = ticketListRequest.begin();
  loading.value = true;
  try {
    const response = await getTicketsApi(buildParams());
    request.commit(() => {
      tickets.value = response.items;
      ticketTotal.value = response.total;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

function searchTickets() {
  ticketPage.value = 1;
  void loadTickets();
}

function resetFilters() {
  filters.ticketId = undefined;
  filters.submitter = '';
  filters.title = '';
  filters.ticketType = '';
  filters.status = '';
  filters.priority = '';
  filters.assignee = '';
  matchMode.value = 'and';
  searchTickets();
}

function changePage(pagination: TablePaginationConfig) {
  ticketPage.value = pagination.current ?? 1;
  void loadTickets();
}

async function submitTicket(payload: TicketCreatePayload) {
  creating.value = true;
  try {
    const ticket = await createTicketApi(payload);
    message.success('工单已提交');
    createOpen.value = false;
    await router.push(`/tickets/${ticket.id}`);
  } finally {
    creating.value = false;
  }
}

function asTicketRecord(record: Record<string, unknown>) {
  return record as unknown as TicketRecord;
}

onMounted(() => void loadTickets());
</script>

<template>
  <Page title="工单管理">
    <div class="min-w-0 space-y-4">
      <ManagementFilterPanel
        :active-filter-count="activeFilterCount"
        :loading="loading"
        @reset="resetFilters"
        @search="searchTickets"
      >
        <div class="management-filter__field">
          <span class="management-filter__label">序号</span>
          <InputNumber
            v-model:value="filters.ticketId"
            :min="1"
            class="w-full"
            size="small"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">提出人</span>
          <Input
            v-model:value="filters.submitter"
            allow-clear
            size="small"
            @press-enter="searchTickets"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">标题</span>
          <Input
            v-model:value="filters.title"
            allow-clear
            size="small"
            @press-enter="searchTickets"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">类型</span>
          <Select
            v-model:value="filters.ticketType"
            allow-clear
            :options="[
              { label: 'REQ', value: 'REQ' },
              { label: 'BUG', value: 'BUG' },
            ]"
            size="small"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">状态</span>
          <Select
            v-model:value="filters.status"
            allow-clear
            :options="ticketStatusOptions"
            size="small"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">优先级</span>
          <Select
            v-model:value="filters.priority"
            allow-clear
            :options="[
              ...ticketPriorityOptions,
              { label: '未设置', value: 'UNSET' },
            ]"
            size="small"
          />
        </div>
        <div class="management-filter__field">
          <span class="management-filter__label">责任人</span>
          <Input
            v-model:value="filters.assignee"
            allow-clear
            size="small"
            @press-enter="searchTickets"
          />
        </div>
        <template #extra>
          <RadioGroup
            v-model:value="matchMode"
            button-style="solid"
            size="small"
          >
            <RadioButton value="and">AND</RadioButton>
            <RadioButton value="or">OR</RadioButton>
          </RadioGroup>
        </template>
      </ManagementFilterPanel>

      <Card class="management-table-card" :body-style="{ padding: 0 }">
        <div class="management-toolbar management-toolbar--table">
          <div class="management-toolbar__group">
            <span>工单列表</span>
            <Tag>{{ ticketTotal }}</Tag>
          </div>
          <div class="management-toolbar__actions management-toolbar__group">
            <Button :loading="loading" size="small" @click="loadTickets">
              <template #icon><RotateCw class="size-4" /></template>
              刷新
            </Button>
            <Button size="small" type="primary" @click="createOpen = true">
              <template #icon><Plus class="size-4" /></template>
              提交工单
            </Button>
          </div>
        </div>
        <Table
          :columns="columns"
          :data-source="tickets"
          :loading="loading"
          :pagination="tablePagination(ticketPage, ticketTotal)"
          :scroll="{ x: 1310 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.key === 'submitter'">
              {{
                userDisplayName(
                  record.submitter_display_name,
                  record.submitter_username,
                )
              }}
            </template>
            <template v-else-if="column.dataIndex === 'ticket_type'">
              <Tag :color="record.ticket_type === 'BUG' ? 'red' : 'blue'">
                {{ record.ticket_type }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'title'">
              <Tooltip :title="record.title">
                <Button
                  class="max-w-full px-0"
                  type="link"
                  @click="router.push(`/tickets/${record.id}`)"
                >
                  <span class="block truncate">{{ record.title }}</span>
                </Button>
              </Tooltip>
            </template>
            <template v-else-if="column.dataIndex === 'status'">
              <Tag :color="ticketStatusColor(asTicketRecord(record))">
                {{ ticketStatusLabel(asTicketRecord(record)) }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'priority'">
              {{ ticketPriorityLabel(record.priority) }}
            </template>
            <template v-else-if="column.key === 'assignee'">
              {{
                userDisplayName(
                  record.assignee_display_name,
                  record.assignee_username,
                )
              }}
            </template>
            <template v-else-if="column.dataIndex === 'planned_completion_at'">
              {{ formatTicketTime(text) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Button
                size="small"
                type="link"
                @click="router.push(`/tickets/${record.id}`)"
              >
                <template #icon><Eye class="size-4" /></template>
                详情
              </Button>
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <TicketContentModal
      :loading="creating"
      :open="createOpen"
      @cancel="createOpen = false"
      @submit="submitTicket"
    />
  </Page>
</template>
