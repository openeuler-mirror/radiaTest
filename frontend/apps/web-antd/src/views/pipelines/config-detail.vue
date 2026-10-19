<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  PipelineConfigRecord,
  PipelineExecutionRecord,
  PipelineTypeRecord,
} from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, Plus, RotateCw } from '@vben/icons';

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
  deletePipelineConfigApi,
  deletePipelineExecutionApi,
  deletePipelineExecutionsByConfigApi,
  getPipelineConfigsApi,
  getPipelineExecutionsApi,
  getPipelineTypesApi,
  triggerPipelineApi,
} from '#/api';
import { parseAPIError } from '#/api/api-error';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const triggerLoading = ref(false);
const deleteLoading = ref(false);
const config = ref<null | PipelineConfigRecord>(null);
const pipelineTypes = ref<PipelineTypeRecord[]>([]);
const executions = ref<PipelineExecutionRecord[]>([]);

const executionColumns: TableColumnsType = [
  { dataIndex: 'triggered_at', title: '触发时间', width: 180 },
  { dataIndex: 'completed_at', title: '完成时间', width: 180 },
  { dataIndex: 'status', title: '状态', width: 100 },
  { dataIndex: 'versions', title: '版本', width: 200 },
  { dataIndex: 'archs', title: '架构', width: 160 },
  { dataIndex: 'triggered_by', title: '触发者', width: 120 },
  { key: 'actions', title: '操作', width: 200, fixed: 'right' },
];

const pipelineType = computed(() =>
  pipelineTypes.value.find((t) => t.name === config.value?.pipeline_type),
);

const isDirectRun = computed(
  () => pipelineType.value?.strategy_kind === 'direct_run',
);

const configLabel = computed(() => {
  if (!config.value) return '';
  return `${config.value.name} (${config.value.pipeline_type})`;
});

const triggerForm = reactive({ image_round: '' });
const triggerModalOpen = ref(false);

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

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

async function loadConfig() {
  const id = route.params.id as string;
  loading.value = true;
  try {
    const allConfigs = await getPipelineConfigsApi();
    config.value = allConfigs.find((c) => c.id === id) ?? null;
    if (config.value) {
      document.title = `配置: ${config.value.name}`;
    }
    if (!config.value) {
      message.error('配置不存在');
      router.push('/pipelines');
    }
  } finally {
    loading.value = false;
  }
}

async function loadPipelineTypes() {
  try {
    pipelineTypes.value = await getPipelineTypesApi();
  } catch {
    // 类型加载失败不阻塞页面
  }
}

async function loadExecutions() {
  if (!config.value) return;
  const items = await getPipelineExecutionsApi({
    config_id: config.value.id,
  });
  executions.value = items;
}

async function refresh() {
  await loadConfig();
  if (!config.value) return;
  await Promise.all([loadPipelineTypes(), loadExecutions()]);
}

function openTriggerModal() {
  triggerForm.image_round = '';
  if (isDirectRun.value) {
    triggerModalOpen.value = true;
  } else {
    void handleTrigger();
  }
}

async function handleTrigger(imageRound?: string) {
  if (!config.value) return;
  triggerLoading.value = true;
  try {
    const payload: { config_id: string; image_round?: string } = {
      config_id: config.value.id,
    };
    if (imageRound) payload.image_round = imageRound;
    const exec = await triggerPipelineApi(payload);
    message.success('流水线已触发');
    await loadExecutions();
    router.push(`/pipelines/executions/${exec.id}`);
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '触发失败');
  } finally {
    triggerLoading.value = false;
  }
}

async function handleTriggerConfirm() {
  if (isDirectRun.value && !triggerForm.image_round.trim()) {
    message.warning('请填写镜像轮次（image_round）');
    return;
  }
  const imageRound = triggerForm.image_round.trim() || undefined;
  triggerModalOpen.value = false;
  await handleTrigger(imageRound);
}

function openEdit() {
  if (!config.value) return;
  router.push({
    path: '/pipelines',
    query: { edit_config_id: config.value.id },
  });
}

async function handleDeleteExecution(record: PipelineExecutionRecord) {
  Modal.confirm({
    title: '删除执行记录',
    content: `确认删除该执行（${formatTime(record.triggered_at)}）？此操作级联删除其下所有 Runs/RunJobs。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      deleteLoading.value = true;
      try {
        await deletePipelineExecutionApi(record.id);
        message.success('已删除');
        await loadExecutions();
      } catch (error) {
        const detail = parseAPIError(error)?.message ?? '';
        message.error(`删除失败：${detail}`);
      } finally {
        deleteLoading.value = false;
      }
    },
  });
}
async function handleDeleteAllExecutions() {
  if (!config.value) return;
  const configId = config.value.id;
  Modal.confirm({
    title: '批量删除所有执行记录',
    content: `确认删除该配置的所有执行记录？此操作不可逆。`,
    okText: '全部删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      deleteLoading.value = true;
      try {
        await deletePipelineExecutionsByConfigApi(configId);
        message.success('已清空所有执行记录');
        await loadExecutions();
      } catch (error) {
        const detail = parseAPIError(error)?.message ?? '';
        message.error(`删除失败：${detail}`);
      } finally {
        deleteLoading.value = false;
      }
    },
  });
}

async function handleDeleteConfig() {
  if (!config.value) return;
  const configId = config.value.id;
  Modal.confirm({
    title: '删除流水线配置',
    content: '确认删除该配置？如有执行记录需先清空。删除后不可恢复。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      deleteLoading.value = true;
      try {
        await deletePipelineConfigApi(configId);
        message.success('配置已删除');
        router.push('/pipelines');
      } catch (error) {
        const apiError = parseAPIError(error);
        if (apiError?.code === 'conflict') {
          message.error(
            `存在 ${executions.value.length} 条历史执行记录，请先清空再删除配置`,
          );
        } else {
          message.error(`删除失败：${apiError?.message ?? ''}`);
        }
      } finally {
        deleteLoading.value = false;
      }
    },
  });
}

function openExecution(record: PipelineExecutionRecord) {
  router.push(`/pipelines/executions/${record.id}`);
}

onMounted(() => {
  void refresh();
});
</script>

<template>
  <Page title="流水线配置详情">
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
      </div>

      <Card v-if="config" :body-style="{ padding: '16px' }">
        <Descriptions bordered :column="3" size="small">
          <DescriptionsItem label="配置名">
            {{ config.name }}
          </DescriptionsItem>
          <DescriptionsItem label="类型">
            <Tag :color="isDirectRun ? 'green' : 'blue'">
              {{ config.pipeline_type }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="测试框架">
            {{ config.test_framework }}
          </DescriptionsItem>
          <DescriptionsItem label="发行版">
            {{ config.dist || '-' }}
          </DescriptionsItem>
          <DescriptionsItem label="镜像轮次">
            {{ config.image_round || '-' }}
          </DescriptionsItem>
          <DescriptionsItem label="版本">
            {{ (config.versions || []).join(', ') }}
          </DescriptionsItem>
          <DescriptionsItem label="架构" :span="3">
            <Tag v-for="a in config.archs" :key="a" color="blue">{{ a }}</Tag>
          </DescriptionsItem>
        </Descriptions>

        <div class="mt-3 flex gap-2">
          <Button
            type="primary"
            :loading="triggerLoading"
            @click="openTriggerModal"
          >
            <template #icon><Plus class="size-4" /></template>
            触发新执行
          </Button>
          <Button @click="openEdit">编辑配置</Button>
          <Button danger :loading="deleteLoading" @click="handleDeleteConfig">
            删除配置
          </Button>
        </div>
      </Card>

      <Card :body-style="{ padding: 0 }">
        <div class="executions-toolbar">
          <div class="executions-toolbar__left">历史执行记录</div>
          <div class="executions-toolbar__right">
            <Button
              :disabled="executions.length === 0"
              :loading="deleteLoading"
              danger
              size="small"
              @click="handleDeleteAllExecutions"
            >
              全部删除
            </Button>
          </div>
        </div>
        <Table
          :columns="executionColumns"
          :data-source="executions"
          :loading="loading"
          :pagination="{ defaultPageSize: 20, showSizeChanger: true }"
          :scroll="{ x: 1100 }"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template
              v-if="
                ['triggered_at', 'completed_at'].includes(
                  String(column.dataIndex),
                )
              "
            >
              {{
                formatTime(record[String(column.dataIndex)] as null | string)
              }}
            </template>
            <template v-else-if="column.dataIndex === 'status'">
              <Tag :color="statusColor(record.status)">
                {{ statusLabel(record.status) }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'versions'">
              <span class="executions-ellipsis">
                {{ (record.versions || []).join(', ') }}
              </span>
            </template>
            <template v-else-if="column.dataIndex === 'archs'">
              <Tag
                v-for="a in record.archs"
                :key="a"
                color="blue"
                style="margin-bottom: 2px"
              >
                {{ a }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                size="small"
                type="link"
                @click="openExecution(record as PipelineExecutionRecord)"
              >
                查看
              </Button>
              <Button
                :loading="deleteLoading"
                danger
                size="small"
                type="link"
                @click="
                  handleDeleteExecution(record as PipelineExecutionRecord)
                "
              >
                删除
              </Button>
            </template>
          </template>
        </Table>
      </Card>

      <Modal
        v-model:open="triggerModalOpen"
        :confirm-loading="triggerLoading"
        title="触发流水线"
        width="500px"
        @ok="handleTriggerConfirm"
      >
        <div class="space-y-2">
          <div>
            <strong>配置：</strong>
            <span>{{ configLabel }}</span>
          </div>
          <div>
            <strong>镜像轮次（image_round）：</strong>
            <input
              v-model="triggerForm.image_round"
              placeholder="如 round-9（必填）"
              class="trigger-input"
            />
          </div>
        </div>
      </Modal>
    </div>
  </Page>
</template>

<style scoped>
.executions-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
}

.executions-toolbar__left {
  font-weight: 600;
}

.executions-ellipsis {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trigger-input {
  width: 100%;
  padding: 4px 8px;
  margin-top: 4px;
  border: 1px solid rgb(217 217 217);
  border-radius: 4px;
}
</style>
