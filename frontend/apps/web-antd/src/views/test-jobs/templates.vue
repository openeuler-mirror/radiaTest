<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type {
  MugenCaseRecord,
  TestJobDetailRecord,
  TestJobTemplateRecord,
  VMImageRecord,
} from '#/api';

import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Pencil, Play, Plus, RotateCw, Trash2 } from '@vben/icons';

import {
  Button,
  Card,
  message,
  Popconfirm,
  Table,
  Tag,
  Tooltip,
} from 'ant-design-vue';

import {
  deleteTestJobTemplateApi,
  getAllTestCasesApi,
  getTestJobTemplatesApi,
  getVMImagesApi,
} from '#/api';

import { createLatestRequestGuard } from '../_shared/latest-request';
import { tablePagination } from '../_shared/table-pagination';
import TestJobCreateModal from './test-job-create-modal.vue';
import TestJobsTabs from './test-jobs-tabs.vue';

type ModalPurpose = 'create-job' | 'create-template' | 'edit-template';

const router = useRouter();
const templateListRequest = createLatestRequestGuard();
const loading = ref(false);
const optionsLoading = ref(false);
const modalOpen = ref(false);
const modalPurpose = ref<ModalPurpose>('create-template');
const selectedTemplate = ref<null | TestJobTemplateRecord>(null);
const templates = ref<TestJobTemplateRecord[]>([]);
const templatePage = ref(1);
const templateTotal = ref(0);
const cases = ref<MugenCaseRecord[]>([]);
const images = ref<VMImageRecord[]>([]);

const columns: TableColumnsType<TestJobTemplateRecord> = [
  { dataIndex: 'id', fixed: 'left', title: 'ID', width: 80 },
  {
    dataIndex: 'name',
    ellipsis: true,
    fixed: 'left',
    title: '名称',
    width: 220,
  },
  { key: 'image', title: '镜像版本', width: 360 },
  { dataIndex: 'arch', title: '架构', width: 110 },
  { dataIndex: 'env_set_num', title: '环境套数', width: 100 },
  { key: 'case_count', title: 'Suite / Case', width: 140 },
  { ellipsis: true, key: 'availability', title: '可用状态', width: 180 },
  { dataIndex: 'creator_username', title: '创建人', width: 120 },
  { dataIndex: 'updated_at', title: '更新时间', width: 180 },
  { fixed: 'right', key: 'action', title: '', width: 260 },
];

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function formatImage(record: TestJobTemplateRecord) {
  return [record.dist, record.os_version, record.image_round]
    .filter(Boolean)
    .join(' / ');
}

async function loadTemplates() {
  const request = templateListRequest.begin();
  loading.value = true;
  try {
    const response = await getTestJobTemplatesApi(templatePage.value);
    request.commit(() => {
      templates.value = response.items;
      templateTotal.value = response.total;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

async function loadOptions() {
  optionsLoading.value = true;
  try {
    cases.value = await getAllTestCasesApi({ env_type: 'vm' });
    try {
      images.value = await getVMImagesApi();
    } catch {
      images.value = [];
    }
  } finally {
    optionsLoading.value = false;
  }
}

async function openModal(
  purpose: ModalPurpose,
  template: null | TestJobTemplateRecord = null,
) {
  await loadOptions();
  if (purpose !== 'edit-template') {
    if (cases.value.length === 0) {
      message.warning('当前没有可用的 VM 测试用例');
      return;
    }
    if (images.value.length === 0) {
      message.warning('当前无法读取可用 VM 镜像');
      return;
    }
  }
  modalPurpose.value = purpose;
  selectedTemplate.value = template;
  modalOpen.value = true;
}

async function deleteTemplate(record: TestJobTemplateRecord) {
  await deleteTestJobTemplateApi(record.id);
  message.success('任务模板已删除');
  await loadTemplates();
}

async function handleTemplateSaved() {
  await loadTemplates();
}

async function handleJobCreated(job: TestJobDetailRecord) {
  await router.push(`/test-jobs/${job.id}`);
}

function asTemplateRecord(record: Record<string, unknown>) {
  return record as unknown as TestJobTemplateRecord;
}

function changePage(pagination: TablePaginationConfig) {
  templatePage.value = pagination.current ?? 1;
  void loadTemplates();
}

onMounted(() => void loadTemplates());
</script>

<template>
  <Page title="测试任务">
    <div class="space-y-4">
      <TestJobsTabs />

      <Card :body-style="{ padding: '16px' }">
        <div class="management-toolbar">
          <Tag>{{ templateTotal }} 个模板</Tag>
          <div class="management-toolbar__actions management-toolbar__group">
            <Button :loading="loading" @click="loadTemplates">
              <template #icon><RotateCw class="size-4" /></template>
              刷新
            </Button>
            <Button
              :loading="optionsLoading"
              type="primary"
              @click="openModal('create-template')"
            >
              <template #icon><Plus class="size-4" /></template>
              创建模板
            </Button>
          </div>
        </div>
      </Card>

      <Card class="management-table-card" :body-style="{ padding: 0 }">
        <Table
          :columns="columns"
          :data-source="templates"
          :loading="loading"
          :pagination="tablePagination(templatePage, templateTotal)"
          :scroll="{ x: 1750 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.key === 'image'">
              {{ formatImage(asTemplateRecord(record)) }}
            </template>
            <template v-else-if="column.key === 'case_count'">
              {{ record.suite_count }} / {{ record.case_count }}
            </template>
            <template v-else-if="column.key === 'availability'">
              <Tooltip
                :title="
                  record.is_available ? undefined : record.unavailable_reason
                "
              >
                <Tag
                  class="m-0 max-w-full overflow-hidden align-middle"
                  :color="record.is_available ? 'green' : 'orange'"
                >
                  <span class="block truncate">
                    {{
                      record.is_available ? '可用' : record.unavailable_reason
                    }}
                  </span>
                </Tag>
              </Tooltip>
            </template>
            <template v-else-if="column.dataIndex === 'updated_at'">
              {{ formatTime(text) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <div class="management-toolbar__group flex-nowrap">
                <Button
                  :disabled="!record.is_available"
                  size="small"
                  type="link"
                  @click="openModal('create-job', asTemplateRecord(record))"
                >
                  <template #icon><Play class="size-4" /></template>
                  使用
                </Button>
                <Button
                  v-if="record.can_manage"
                  size="small"
                  type="link"
                  @click="openModal('edit-template', asTemplateRecord(record))"
                >
                  <template #icon><Pencil class="size-4" /></template>
                  编辑
                </Button>
                <Popconfirm
                  v-if="record.can_manage"
                  title="确认删除这个任务模板？"
                  @confirm="deleteTemplate(asTemplateRecord(record))"
                >
                  <Button danger size="small" type="link">
                    <template #icon><Trash2 class="size-4" /></template>
                    删除
                  </Button>
                </Popconfirm>
              </div>
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <TestJobCreateModal
      v-model:open="modalOpen"
      :cases="cases"
      :images="images"
      :purpose="modalPurpose"
      :template="selectedTemplate"
      @job-created="handleJobCreated"
      @template-saved="handleTemplateSaved"
    />
  </Page>
</template>
