<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { VersionRecord } from '#/api';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  DatePicker,
  Form,
  FormItem,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Select,
  SelectOption,
  Table,
  TabPane,
  Tabs,
  Tag,
  Textarea,
} from 'ant-design-vue';

import { createVersionApi, deleteVersionApi, listVersionsApi } from '#/api';
import { parseAPIError } from '#/api/api-error';

const router = useRouter();
const activeTab = ref('rc');
const loading = ref(false);
const search = ref('');
const versions = ref<VersionRecord[]>([]);

const modalOpen = ref(false);
const saving = ref(false);
const form = ref({
  name: '',
  version_type: 'INNOVATION',
  rc_round_count: 0,
  start_time: undefined as string | undefined,
  end_time: undefined as string | undefined,
  remark: '',
});

const columns: TableColumnsType = [
  { key: 'name', title: '版本', dataIndex: 'name' },
  { key: 'version_type', title: '版本类型', dataIndex: 'version_type' },
  { key: 'status', title: '状态', dataIndex: 'status' },
  {
    key: 'milestone_count',
    title: 'RC 轮次数',
    dataIndex: 'milestone_count',
    width: 110,
  },
  { key: 'period', title: '起止时间' },
  { key: 'action', title: '操作', width: 120 },
];

const filteredVersions = computed(() =>
  search.value
    ? versions.value.filter((v) =>
        v.name.toLowerCase().includes(search.value.toLowerCase()),
      )
    : versions.value,
);

async function load() {
  loading.value = true;
  try {
    const resp = await listVersionsApi(search.value || undefined);
    versions.value = resp.items;
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '加载版本列表失败');
  } finally {
    loading.value = false;
  }
}

function changeSearch() {
  void load();
}

function openCreate() {
  form.value = {
    name: '',
    version_type: 'INNOVATION',
    rc_round_count: 0,
    start_time: undefined,
    end_time: undefined,
    remark: '',
  };
  modalOpen.value = true;
}

async function submitCreate() {
  if (!form.value.name.trim()) {
    message.warning('请填写版本名称');
    return;
  }
  saving.value = true;
  try {
    await createVersionApi({
      name: form.value.name.trim(),
      version_type: form.value.version_type,
      rc_round_count: form.value.rc_round_count,
      start_time: form.value.start_time,
      end_time: form.value.end_time,
      remark: form.value.remark || null,
    });
    message.success(
      form.value.rc_round_count > 0
        ? `已创建版本并生成 ${form.value.rc_round_count} 个 RC 轮次`
        : '已创建版本',
    );
    modalOpen.value = false;
    void load();
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '创建版本失败');
  } finally {
    saving.value = false;
  }
}

async function onDeleteVersion(v: VersionRecord) {
  try {
    await deleteVersionApi(v.id);
    message.success('已删除版本');
    void load();
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '删除失败');
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <Page title="版本管理" :content-style="{ padding: '16px' }">
    <div class="mb-4">
      <Tabs v-model:active-key="activeTab">
        <TabPane key="rc" tab="RC 版本" />
        <TabPane key="update" tab="Update 版本" />
      </Tabs>
    </div>

    <Card v-if="activeTab === 'rc'" :bordered="false">
      <template #title>RC 版本列表</template>
      <template #extra>
        <div class="flex items-center gap-2">
          <Input
            v-model:value="search"
            placeholder="搜索版本..."
            allow-clear
            style="width: 240px"
            @change="changeSearch"
          />
          <Button type="primary" @click="openCreate">新建版本</Button>
        </div>
      </template>
      <Table
        :columns="columns"
        :data-source="filteredVersions"
        :loading="loading"
        row-key="id"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'version_type'">
            <Tag v-if="record.version_type" color="blue">
              {{ record.version_type }}
            </Tag>
            <span v-else>—</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag v-if="record.status === 'finished'" color="default">
              已结束
            </Tag>
            <Tag v-else color="green">测试中</Tag>
          </template>
          <template v-else-if="column.key === 'period'">
            {{ record.start_time ?? '—' }} ~ {{ record.end_time ?? '—' }}
          </template>
          <template v-else-if="column.key === 'action'">
            <Button
              size="small"
              type="link"
              @click="router.push(`/versions/${record.id}`)"
            >
              查看
            </Button>
            <Popconfirm
              title="确认删除该版本？"
              :disabled="record.milestone_count > 0"
              @confirm="() => onDeleteVersion(record as VersionRecord)"
            >
              <Button
                size="small"
                type="link"
                danger
                :disabled="record.milestone_count > 0"
              >
                删除
              </Button>
            </Popconfirm>
          </template>
        </template>
      </Table>
    </Card>

    <Card v-else :bordered="false">
      <div
        class="flex flex-col items-center justify-center py-20 text-gray-400"
      >
        <div class="text-3xl">U</div>
        <div class="mt-2">Update 版本测试监管规划中</div>
        <div class="text-xs">
          将在此展示各模块执行 / 分析 / 可交付进展（占位，后续实现）
        </div>
      </div>
    </Card>

    <Modal
      v-model:open="modalOpen"
      title="新建版本"
      :confirm-loading="saving"
      ok-text="提交"
      cancel-text="取消"
      @ok="submitCreate"
    >
      <Form layout="vertical">
        <FormItem label="版本名称" required>
          <Input
            v-model:value="form.name"
            placeholder="如 openEuler-26.09-DevStation"
          />
        </FormItem>
        <FormItem label="版本类型">
          <Select v-model:value="form.version_type">
            <SelectOption value="INNOVATION">INNOVATION</SelectOption>
            <SelectOption value="LTS">LTS</SelectOption>
            <SelectOption value="LTS-SPx">LTS-SPx</SelectOption>
          </Select>
        </FormItem>
        <FormItem label="RC 轮次数">
          <InputNumber v-model:value="form.rc_round_count" :min="0" :max="24" />
          <div class="text-xs text-gray-400">
            创建后自动生成 round1…roundN 里程碑骨架，构建 URL 后续在里程碑上登记
          </div>
        </FormItem>
        <FormItem label="起止时间">
          <div class="flex gap-2">
            <DatePicker
              v-model:value="form.start_time"
              class="flex-1"
              value-format="YYYY-MM-DD"
              placeholder="开始日期"
            />
            <DatePicker
              v-model:value="form.end_time"
              class="flex-1"
              value-format="YYYY-MM-DD"
              placeholder="结束日期"
            />
          </div>
        </FormItem>
        <FormItem label="备注">
          <Textarea v-model:value="form.remark" :rows="2" placeholder="可选" />
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>
