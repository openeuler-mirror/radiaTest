<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { MilestoneRecord, VersionRecord } from '#/api';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  DatePicker,
  Form,
  FormItem,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  SelectOption,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  createMilestoneApi,
  deleteMilestoneApi,
  listVersionMilestonesApi,
  listVersionsApi,
} from '#/api';
import { parseAPIError } from '#/api/api-error';

const route = useRoute();
const router = useRouter();
const versionId = route.params.id as string;

const version = ref<null | VersionRecord>(null);
const milestones = ref<MilestoneRecord[]>([]);
const loading = ref(false);
const search = ref('');

const modalOpen = ref(false);
const saving = ref(false);
const form = ref({
  name: '',
  kernel_variant: '',
  build_url: '',
  start_time: undefined as string | undefined,
  end_time: undefined as string | undefined,
  base_milestone_id: undefined as string | undefined,
});
const derivedLabel = ref('');

function deriveLabel(url: string) {
  const m = url.match(/(?:rc\d+|[a-z]+)_openeuler-[0-9-]+/);
  derivedLabel.value = m ? m[0] : '';
}

const currentRound = computed(() => {
  const running = milestones.value.find(
    (m) => m.latest_compare?.status === 'running',
  );
  return running;
});

const columns: TableColumnsType = [
  { key: 'name', title: '轮次', dataIndex: 'name' },
  { key: 'period', title: '起止时间' },
  { key: 'base', title: '比对基准', dataIndex: 'compare_base_name' },
  { key: 'kernel', title: 'kernel 变体', dataIndex: 'kernel_variant' },
  { key: 'compare', title: '最近比对' },
  { key: 'pxe', title: '94 装机源', dataIndex: 'has_pxe_source' },
  { key: 'action', title: '操作', width: 140 },
];

const filteredMilestones = computed(() =>
  search.value
    ? milestones.value.filter((m) =>
        m.name.toLowerCase().includes(search.value.toLowerCase()),
      )
    : milestones.value,
);

async function loadVersion() {
  try {
    const list = await listVersionsApi();
    version.value = list.items.find((v) => v.id === versionId) ?? null;
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '加载版本失败');
  }
}

async function loadMilestones() {
  loading.value = true;
  try {
    milestones.value = await listVersionMilestonesApi(versionId);
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '加载里程碑失败');
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  derivedLabel.value = '';
  const last = milestones.value[milestones.value.length - 1];
  form.value = {
    name: `round${milestones.value.filter((m) => /^round\d+$/.test(m.name)).length + 1}`,
    kernel_variant: '',
    build_url: '',
    start_time: undefined,
    end_time: undefined,
    base_milestone_id: last?.id ?? undefined,
  };
  modalOpen.value = true;
}

async function submitCreate() {
  if (!form.value.name.trim()) {
    message.warning('请填写轮次名称');
    return;
  }
  if (!form.value.build_url.trim()) {
    message.warning('请填写比对构建根 URL');
    return;
  }
  saving.value = true;
  try {
    await createMilestoneApi({
      version_id: versionId,
      name: form.value.name.trim(),
      kernel_variant: form.value.kernel_variant.trim() || null,
      build_url: form.value.build_url.trim(),
      compare_base_milestone_id: form.value.base_milestone_id,
      start_time: form.value.start_time,
      end_time: form.value.end_time,
    });
    message.success('已创建里程碑');
    modalOpen.value = false;
    void loadMilestones();
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '创建里程碑失败');
  } finally {
    saving.value = false;
  }
}

async function onDeleteMilestone(m: MilestoneRecord) {
  try {
    await deleteMilestoneApi(m.id);
    message.success('已删除里程碑');
    void loadMilestones();
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '删除失败');
  }
}

onMounted(() => {
  void loadVersion();
  void loadMilestones();
});
</script>

<template>
  <Page title="版本详情" :content-style="{ padding: '16px' }">
    <div class="mb-3">
      <a
        class="text-sm"
        href="javascript:void(0)"
        @click="router.push('/versions')"
      >
        返回 RC 版本
      </a>
    </div>

    <Card :bordered="false" class="mb-4">
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="m-0">{{ version?.name ?? versionId }}</h2>
            <Tag v-if="version?.version_type" color="blue">
              {{ version.version_type }}
            </Tag>
            <Tag v-if="version?.status === 'finished'" color="default">
              已结束
            </Tag>
            <Tag v-else color="green">测试中</Tag>
          </div>
          <div class="mt-1 text-sm text-gray-500">
            {{ version?.start_time ?? '—' }} ~ {{ version?.end_time ?? '—' }} ·
            {{ milestones.length }} 个轮次 · 当前轮
            {{ currentRound?.name ?? '—' }}
          </div>
        </div>
        <Button type="primary" @click="openCreate">创建里程碑</Button>
      </div>
    </Card>

    <Card :bordered="false">
      <template #title>RC 里程碑（轮次）</template>
      <template #extra>
        <Input
          v-model:value="search"
          placeholder="搜索轮次..."
          allow-clear
          style="width: 240px"
          @change="loadMilestones"
        />
      </template>
      <Table
        :columns="columns"
        :data-source="filteredMilestones"
        :loading="loading"
        row-key="id"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span class="font-mono">{{ record.name }}</span>
            <Tag
              v-if="record.latest_compare?.status === 'running'"
              color="blue"
              class="ml-1"
            >
              当前轮
            </Tag>
          </template>
          <template v-else-if="column.key === 'period'">
            {{ record.start_time ?? '—' }} ~ {{ record.end_time ?? '—' }}
          </template>
          <template v-else-if="column.key === 'base'">
            <span class="font-mono">{{ record.compare_base_name ?? '—' }}</span>
          </template>
          <template v-else-if="column.key === 'kernel'">
            <span class="font-mono">{{ record.kernel_variant ?? '—' }}</span>
          </template>
          <template v-else-if="column.key === 'compare'">
            <template v-if="record.latest_compare?.status === 'succeeded'">
              <Tag color="green">
                已完成 · {{ record.latest_compare.total_changed ?? 0 }} 项变更
              </Tag>
            </template>
            <Tag
              v-else-if="record.latest_compare?.status === 'failed'"
              color="red"
            >
              失败
            </Tag>
            <Tag v-else-if="record.latest_compare" color="orange">
              {{ record.latest_compare.status }}
            </Tag>
            <Tag v-else>未比对</Tag>
          </template>
          <template v-else-if="column.key === 'pxe'">
            <Tag v-if="record.has_pxe_source" color="green">有</Tag>
            <Tag v-else>无</Tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <Button
              size="small"
              type="primary"
              @click="
                router.push(`/versions/${versionId}/milestones/${record.id}`)
              "
            >
              测试管理
            </Button>
            <Popconfirm
              title="确认删除该里程碑？"
              :disabled="!!record.latest_compare"
              @confirm="() => onDeleteMilestone(record as MilestoneRecord)"
            >
              <Button
                size="small"
                type="link"
                danger
                :disabled="!!record.latest_compare"
              >
                删除
              </Button>
            </Popconfirm>
          </template>
        </template>
      </Table>
    </Card>

    <Modal
      v-model:open="modalOpen"
      title="创建里程碑（RC 轮次）"
      :confirm-loading="saving"
      ok-text="提交"
      cancel-text="取消"
      @ok="submitCreate"
    >
      <Form layout="vertical">
        <FormItem label="轮次名称" required>
          <Input v-model:value="form.name" placeholder="如 round8 / release" />
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
        <FormItem label="kernel 变体">
          <Input
            v-model:value="form.kernel_variant"
            placeholder="如 6.18 / 6.6"
          />
        </FormItem>
        <FormItem label="比对基准（默认前一轮）">
          <Select v-model:value="form.base_milestone_id" allow-clear>
            <SelectOption v-for="m in milestones" :key="m.id" :value="m.id">
              {{ m.name }}
            </SelectOption>
          </Select>
        </FormItem>
        <FormItem label="比对构建根 URL" required>
          <Input
            v-model:value="form.build_url"
            placeholder="http://121.36.84.172/dailybuild/EBS-…/rcN_openeuler-…/26.09-with-kernel-6.6/"
            @update:value="deriveLabel(form.build_url)"
          />
        </FormItem>
        <FormItem label="轮次标签（自动推导）">
          <Input :value="derivedLabel" disabled placeholder="rcN_openeuler-…" />
        </FormItem>
        <div class="mb-1 text-xs text-gray-400">
          该轮 94 是否有装机源：保存后按轮次标签查询（只读提示，不校验）
        </div>
      </Form>
    </Modal>
  </Page>
</template>
