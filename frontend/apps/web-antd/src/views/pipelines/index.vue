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
  PipelineTriggerPayload,
  PipelineTypeRecord,
  TestModuleTemplateRecord,
} from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Eye, Plus, RotateCw } from '@vben/icons';

import {
  Button,
  Card,
  Checkbox,
  Form,
  FormItem,
  Input,
  InputNumber,
  message,
  Modal,
  Segmented,
  Select,
  SelectOption,
  Table,
  TabPane,
  Tabs,
  Tag,
  Textarea,
} from 'ant-design-vue';

import {
  createModuleTemplateApi,
  createPipelineConfigApi,
  getKnownVersions,
  getModuleTemplatesApi,
  getMugenSuitesApi,
  getPipelineConfigsApi,
  getPipelineExecutionsApi,
  getPipelineTypesApi,
  getVMImagesApi,
  triggerPipelineApi,
  updateModuleTemplateApi,
  updatePipelineConfigApi,
} from '#/api';
import { parseAPIError } from '#/api/api-error';

import ReleaseConfigFields from './release-config-fields.vue';

const router = useRouter();
const activeTab = ref('configs');

// Config state
const loading = ref(false);
const runsLoading = ref(false);
const triggerLoading = ref(false);
const configModalOpen = ref(false);
const savingConfig = ref(false);
const configs = ref<PipelineConfigRecord[]>([]);
const executions = ref<PipelineExecutionRecord[]>([]);
const editingConfig = ref<null | PipelineConfigRecord>(null);
// release 配置字段组件 ref（统一弹窗内 pipeline_type=release 时渲染）
const releaseFields = ref<InstanceType<typeof ReleaseConfigFields> | null>(
  null,
);

// Config filter state
const configTypeFilter = ref<string>('all');
const configNameSearch = ref('');

const pipelineTypes = ref<PipelineTypeRecord[]>([]);

const configTypeOptions = computed(() => [
  { label: '全部', value: 'all' },
  ...pipelineTypes.value.map((t) => ({ label: t.name, value: t.name })),
]);

const templateTypeFilter = ref<string>('update');

const templateTypeOptions = computed(() => [
  { label: '全部', value: 'all' },
  ...pipelineTypes.value.map((t) => ({ label: t.name, value: t.name })),
]);

// Release suite state
const mugenSuites = ref<string[]>([]);
const mugenSuitesLoading = ref(false);

// Template state
const templates = ref<TestModuleTemplateRecord[]>([]);
const templateModalOpen = ref(false);
const savingTemplate = ref(false);
const editingTemplate = ref<null | TestModuleTemplateRecord>(null);

const knownVersions = getKnownVersions();

// VM images for version dropdown (linked to official mirror for update type)
const vmImages = ref<{ image_round: string; os_version: string }[]>([]);

const versionOptions = computed(() => {
  // Merge hardcoded knownVersions with versions from VM image discovery.
  // For update type: these come from the official mirror (image_round="official").
  // For release type: iteration rounds also appear (image_round="round-N").
  const fromImages = vmImages.value.map((img) => img.os_version);
  return [...new Set([...knownVersions, ...fromImages])].toSorted();
});

const configForm = reactive({
  archs: [] as string[],
  dist: '',
  image_round: '',
  module_template_ids: [] as string[],
  name: '',
  pkgcmd_physical_enabled: true,
  pkgserver_physical_enabled: true,
  pkgunion_physical_enabled: true,
  pipeline_type: 'update',
  repo_base_url: 'http://121.36.84.172/repo.openeuler.org',
  suites: [] as string[],
  versions: [] as string[],
});

const templateForm = reactive({
  case_filter: 'none',
  display_name: '',
  env_set_num: 1,
  env_type: 'vm' as string,
  mugen_exec_command: '' as string,
  suite_name: '',
  name: '',
  node_num: 1,
  pipeline_type: 'update',
  post_env_script: '',
  pre_env_script: '',
  rerun_env_script: '',
  result_parser: 'none',
  skip_packages: [] as string[],
  test_framework: 'mugen',
});

const configColumns: TableColumnsType<PipelineConfigRecord> = [
  { dataIndex: 'name', title: '配置名称', width: 200 },
  { dataIndex: 'pipeline_type', title: '类型', width: 100 },
  { key: 'versions', title: '测试版本', width: 300 },
  { key: 'archs', title: '架构', width: 160 },
  { key: 'modules', title: '模块', width: 300 },
  { key: 'latest_execution', title: '最新执行结果', width: 200 },
  { fixed: 'right', key: 'action', title: '', width: 140 },
];

const executionColumns: TableColumnsType<PipelineExecutionRecord> = [
  { dataIndex: 'config_name', title: '配置名', width: 200 },
  { key: 'versions', title: '测试版本', width: 300 },
  { key: 'archs', title: '架构', width: 160 },
  { dataIndex: 'status', title: '状态', width: 120 },
  { dataIndex: 'triggered_by', title: '触发者', width: 120 },
  { dataIndex: 'triggered_at', title: '触发时间', width: 180 },
  { dataIndex: 'completed_at', title: '完成时间', width: 180 },
  { fixed: 'right', key: 'action', title: '', width: 90 },
];

const templateColumns: TableColumnsType<TestModuleTemplateRecord> = [
  { dataIndex: 'display_name', title: '模块名称', width: 160 },
  { dataIndex: 'name', title: '标识', width: 120 },
  { dataIndex: 'suite_name', title: 'Mugen Suite', width: 180 },
  { key: 'config', title: '执行配置', width: 160 },
  { key: 'split', title: 'env_type', width: 120 },
  { key: 'parser', title: '结果解析器', width: 120 },
  { dataIndex: 'result_parser', title: '', width: 0, class: 'hidden' },
  { fixed: 'right', key: 'action', title: '', width: 80 },
];

const filteredConfigs = computed<PipelineConfigRecord[]>(() => {
  const keyword = configNameSearch.value.trim().toLowerCase();
  return configs.value.filter((c) => {
    if (
      configTypeFilter.value !== 'all' &&
      c.pipeline_type !== configTypeFilter.value
    ) {
      return false;
    }
    if (keyword && !c.name.toLowerCase().includes(keyword)) return false;
    return true;
  });
});

function pipelineTypeColor(type: string) {
  const pt = pipelineTypes.value.find((t) => t.name === type);
  if (pt?.strategy_kind === 'direct_run') return 'green';
  return 'blue';
}

function pipelineTypeStrategyKind(type: string): string {
  return pipelineTypes.value.find((t) => t.name === type)?.strategy_kind ?? '';
}

function isDirectRunType(type: string): boolean {
  return pipelineTypeStrategyKind(type) === 'direct_run';
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    cancelled: 'default',
    cancelling: 'warning',
    running: 'processing',
    succeeded: 'green',
    failed: 'red',
    pending: 'default',
  };
  return map[status] ?? 'default';
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    cancelled: '已取消',
    cancelling: '取消中',
    running: '执行中',
    succeeded: '成功',
    failed: '失败',
    pending: '等待',
  };
  return map[status] ?? status;
}

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function templateNames(config: PipelineConfigRecord) {
  const ids = (config.config_data?.module_template_ids as string[]) ?? [];
  return ids
    .map((id) => templates.value.find((t) => t.id === id)?.display_name ?? '?')
    .join(', ');
}

function templateConfig(t: TestModuleTemplateRecord) {
  return `${t.env_set_num} 套 × ${t.node_num} 节点`;
}

// --- Config CRUD ---

function openCreateConfig() {
  editingConfig.value = null;
  configForm.name = '';
  configForm.versions = [];
  configForm.archs = ['aarch64', 'x86_64'];
  configForm.repo_base_url = 'http://121.36.84.172/repo.openeuler.org';
  configForm.module_template_ids = templates.value.map((t) => t.id);
  configForm.pkgcmd_physical_enabled = true;
  configForm.pkgserver_physical_enabled = true;
  configForm.pkgunion_physical_enabled = true;
  configForm.pipeline_type = 'update';
  configForm.suites = [];
  configForm.dist = 'openEuler';
  configForm.image_round = 'official';
  configModalOpen.value = true;
}

function openEditConfig(config: PipelineConfigRecord) {
  editingConfig.value = config;
  configForm.name = config.name;
  configForm.pipeline_type = config.pipeline_type || 'update';
  // release 走统一弹窗内的 ReleaseConfigFields（:config=editingConfig 驱动 hydrate）
  if (config.pipeline_type === 'release') {
    configModalOpen.value = true;
    return;
  }
  configForm.versions = [...config.versions];
  configForm.archs = [...config.archs];
  configForm.repo_base_url =
    (config.config_data?.repo_base_url as string) ??
    'http://121.36.84.172/repo.openeuler.org';
  configForm.module_template_ids = [
    ...((config.config_data?.module_template_ids as string[]) ?? []),
  ];
  configForm.pkgcmd_physical_enabled =
    (config.config_data?.pkgcmd_physical_enabled as boolean | undefined) ??
    true;
  configForm.pkgserver_physical_enabled =
    (config.config_data?.pkgserver_physical_enabled as boolean | undefined) ??
    true;
  configForm.pkgunion_physical_enabled =
    (config.config_data?.pkgunion_physical_enabled as boolean | undefined) ??
    true;
  configForm.dist = config.dist ?? '';
  configForm.image_round = config.image_round ?? '';
  if (isDirectRunType(configForm.pipeline_type)) {
    const suites: string[] = [];
    const ids = (config.config_data?.module_template_ids as string[]) ?? [];
    for (const id of ids) {
      const t = templates.value.find((x) => x.id === id);
      if (t?.suite_name) suites.push(t.suite_name);
    }
    configForm.suites = [...new Set(suites)];
  } else {
    configForm.suites = [];
  }
  configModalOpen.value = true;
}

function openConfigHistory(config: PipelineConfigRecord) {
  router.push(`/pipelines/configs/${config.id}/executions`);
}

function onVersionsChange() {
  // Auto-fill dist and image_round based on pipeline_type and selected versions.
  // - update: dist="openEuler", image_round="official" (from official mirror)
  // - direct_run: dist="openEuler", image_round="" (set at trigger time)
  configForm.dist = 'openEuler';
  configForm.image_round = isDirectRunType(configForm.pipeline_type)
    ? ''
    : 'official';
}

async function handleSaveConfig() {
  if (!configForm.name.trim()) {
    message.warning('请填写配置名称');
    return;
  }
  // release 走 ReleaseConfigFields（cascading + 内核变体 + case 选择器）
  if (configForm.pipeline_type === 'release') {
    const fields = releaseFields.value;
    if (!fields) {
      message.warning('release 表单未就绪');
      return;
    }
    const err = fields.validate();
    if (err) {
      message.warning(err);
      return;
    }
    const data = fields.getData();
    savingConfig.value = true;
    try {
      const payload = {
        name: configForm.name,
        pipeline_type: 'release' as const,
        ...data,
      };
      if (editingConfig.value) {
        await updatePipelineConfigApi(editingConfig.value.id, payload);
        message.success('配置已更新');
      } else {
        await createPipelineConfigApi(payload);
        message.success('配置已创建');
      }
      configModalOpen.value = false;
      await loadConfigs();
    } catch {
      message.error('保存失败');
    } finally {
      savingConfig.value = false;
    }
    return;
  }
  if (configForm.versions.length === 0) {
    message.warning('请至少选择一个版本');
    return;
  }
  if (configForm.archs.length === 0) {
    message.warning('请至少选择一个架构');
    return;
  }
  const isDirectRun = isDirectRunType(configForm.pipeline_type);
  if (isDirectRun && configForm.suites.length === 0) {
    message.warning('请至少选择一个 Suite');
    return;
  }
  if (!isDirectRun && configForm.module_template_ids.length === 0) {
    message.warning('请至少选择一个模块');
    return;
  }

  savingConfig.value = true;
  try {
    const configData = isDirectRun
      ? { suites: configForm.suites }
      : {
          module_template_ids: configForm.module_template_ids,
          pkgcmd_physical_enabled: configForm.pkgcmd_physical_enabled,
          pkgserver_physical_enabled: configForm.pkgserver_physical_enabled,
          pkgunion_physical_enabled: configForm.pkgunion_physical_enabled,
          repo_base_url: configForm.repo_base_url,
        };
    if (editingConfig.value) {
      await updatePipelineConfigApi(editingConfig.value.id, {
        archs: configForm.archs,
        config_data: configData,
        dist: configForm.dist || null,
        image_round: configForm.image_round,
        name: configForm.name,
        pipeline_type: configForm.pipeline_type,
        versions: configForm.versions,
      });
      message.success('配置已更新');
    } else {
      await createPipelineConfigApi({
        archs: configForm.archs,
        config_data: configData,
        dist: configForm.dist || null,
        image_round: configForm.image_round,
        name: configForm.name,
        pipeline_type: configForm.pipeline_type,
        versions: configForm.versions,
      });
      message.success('配置已创建');
    }
    configModalOpen.value = false;
    await loadConfigs();
  } catch {
    message.error('保存失败');
  } finally {
    savingConfig.value = false;
  }
}

// Trigger modal state (for direct_run types that require trigger-level image_round)
const triggerModalOpen = ref(false);
const triggerConfig = ref<null | PipelineConfigRecord>(null);
const triggerForm = reactive({
  image_round: '',
});

const has64kVersion = computed(() =>
  configForm.versions.some((v: string) => v.endsWith('-64k')),
);

const triggerConfigLabel = computed(() => {
  if (!triggerConfig.value) return '';
  return `${triggerConfig.value.name} (${triggerConfig.value.pipeline_type})`;
});

function handleTriggerClick(record: PipelineConfigRecord) {
  triggerConfig.value = record;
  triggerForm.image_round = '';
  if (record.pipeline_type === 'release') {
    // release 触发无参数：用配置里的 image_round（spec §9.3 配置级轮次）。
    void handleTrigger(record);
  } else if (isDirectRunType(record.pipeline_type)) {
    // 其他 direct_run 类型仍支持触发级 image_round 覆盖。
    triggerModalOpen.value = true;
  } else {
    // update 等：直接用 config-level image_round 触发。
    void handleTrigger(record);
  }
}

async function handleTrigger(
  record: PipelineConfigRecord,
  imageRound?: string,
) {
  triggerLoading.value = true;
  try {
    const payload: PipelineTriggerPayload = {
      config_id: record.id,
    };
    if (imageRound !== undefined) {
      payload.image_round = imageRound;
    }
    const exec = await triggerPipelineApi(payload);
    message.success('流水线已触发');
    await loadRuns();
    router.push(`/pipelines/executions/${exec.id}`);
  } catch (error) {
    message.error(parseAPIError(error)?.message ?? '触发失败');
  } finally {
    triggerLoading.value = false;
  }
}

async function handleTriggerConfirm() {
  if (!triggerConfig.value) return;
  if (
    isDirectRunType(triggerConfig.value.pipeline_type) &&
    !triggerForm.image_round.trim()
  ) {
    message.warning('请填写镜像轮次（image_round）');
    return;
  }
  const imageRound = triggerForm.image_round.trim() || undefined;
  triggerModalOpen.value = false;
  await handleTrigger(triggerConfig.value, imageRound);
}

// --- Template CRUD ---

function openCreateTemplate() {
  editingTemplate.value = null;
  Object.assign(templateForm, {
    case_filter: 'none',
    display_name: '',
    env_set_num: 1,
    env_type: 'vm',
    mugen_exec_command: '',
    suite_name: '',
    name: '',
    node_num: 1,
    pipeline_type:
      templateTypeFilter.value === 'all' ? 'update' : templateTypeFilter.value,
    post_env_script: '',
    pre_env_script: '',
    rerun_env_script: '',
    result_parser: 'none',
    skip_packages: [],
    test_framework: 'mugen',
  });
  templateModalOpen.value = true;
}

function openEditTemplate(t: TestModuleTemplateRecord) {
  editingTemplate.value = t;
  Object.assign(templateForm, {
    case_filter: t.case_filter,
    display_name: t.display_name,
    env_set_num: t.env_set_num,
    env_type: t.env_type,
    mugen_exec_command: t.mugen_exec_command || '',
    suite_name: t.suite_name,
    name: t.name,
    node_num: t.node_num,
    post_env_script: t.post_env_script,
    pre_env_script: t.pre_env_script,
    rerun_env_script: t.rerun_env_script,
    result_parser: t.result_parser,
    skip_packages: [...t.skip_packages],
    test_framework: t.test_framework || 'mugen',
  });
  templateModalOpen.value = true;
}

async function handleSaveTemplate() {
  if (!templateForm.name.trim()) {
    message.warning('请填写模块标识');
    return;
  }
  if (!templateForm.display_name.trim()) {
    message.warning('请填写模块名称');
    return;
  }
  if (!templateForm.suite_name.trim()) {
    message.warning('请填写 Mugen Suite');
    return;
  }

  savingTemplate.value = true;
  try {
    if (editingTemplate.value) {
      await updateModuleTemplateApi(editingTemplate.value.id, {
        ...templateForm,
      });
      message.success('模块已更新');
    } else {
      await createModuleTemplateApi({ ...templateForm });
      message.success('模块已创建');
    }
    templateModalOpen.value = false;
    await loadTemplates();
  } catch {
    message.error('保存失败');
  } finally {
    savingTemplate.value = false;
  }
}

// --- Data loading ---

async function loadConfigs() {
  loading.value = true;
  try {
    configs.value = await getPipelineConfigsApi();
  } finally {
    loading.value = false;
  }
}

async function loadMugenSuites() {
  mugenSuitesLoading.value = true;
  try {
    mugenSuites.value = await getMugenSuitesApi();
  } finally {
    mugenSuitesLoading.value = false;
  }
}

async function loadRuns() {
  runsLoading.value = true;
  try {
    executions.value = await getPipelineExecutionsApi({ limit: 20 });
  } finally {
    runsLoading.value = false;
  }
}

async function loadTemplates() {
  const params =
    templateTypeFilter.value === 'all'
      ? undefined
      : { pipeline_type: templateTypeFilter.value };
  templates.value = await getModuleTemplatesApi(params);
}

function openDetail(record: PipelineExecutionRecord) {
  router.push(`/pipelines/executions/${record.id}`);
}

function onConfigModalOpenChange(open: boolean) {
  if (!open) return;
  if (
    isDirectRunType(configForm.pipeline_type) &&
    mugenSuites.value.length === 0
  )
    void loadMugenSuites();
}

async function loadPipelineTypes() {
  try {
    pipelineTypes.value = await getPipelineTypesApi();
  } catch {
    message.error('加载流水线类型失败');
  }
}

async function loadVMImages() {
  try {
    vmImages.value = await getVMImagesApi();
  } catch {
    // 镜像仓库不可达不阻塞页面
  }
}

onMounted(() => {
  void loadTemplates();
  void loadConfigs();
  void loadRuns();
  void loadPipelineTypes();
  void loadVMImages();
});
</script>

<template>
  <Page title="流水线">
    <div class="space-y-4">
      <Tabs v-model:active-key="activeTab">
        <TabPane key="configs" tab="Pipeline 配置">
          <Card :body-style="{ padding: 0 }">
            <div class="pipeline-toolbar">
              <div class="pipeline-toolbar__left">
                <Segmented
                  v-model:value="configTypeFilter"
                  :options="configTypeOptions"
                />
                <Input
                  v-model:value="configNameSearch"
                  allow-clear
                  placeholder="按名称搜索"
                  style="width: 240px"
                />
              </div>
              <div class="pipeline-toolbar__right">
                <Button :loading="loading" @click="loadConfigs">
                  <template #icon><RotateCw class="size-4" /></template>
                  刷新
                </Button>
                <Button type="primary" @click="openCreateConfig">
                  <template #icon><Plus class="size-4" /></template>
                  创建配置
                </Button>
              </div>
            </div>
            <Table
              :columns="configColumns"
              :data-source="filteredConfigs"
              :loading="loading"
              :pagination="false"
              row-key="id"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.dataIndex === 'pipeline_type'">
                  <Tag :color="pipelineTypeColor(record.pipeline_type)">
                    {{ record.pipeline_type }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'versions'">
                  <Tag
                    v-for="v in record.versions"
                    :key="v"
                    style="margin-bottom: 2px"
                  >
                    {{ v }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'archs'">
                  <Tag v-for="a in record.archs" :key="a" color="blue">
                    {{ a }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'modules'">
                  <span class="pipeline-cell-muted">
                    {{ templateNames(record as PipelineConfigRecord) }}
                  </span>
                </template>
                <template v-else-if="column.key === 'latest_execution'">
                  <template v-if="record.latest_execution">
                    <Tag :color="statusColor(record.latest_execution.status)">
                      {{ statusLabel(record.latest_execution.status) }}
                    </Tag>
                    <div class="pipeline-cell-muted">
                      {{ formatTime(record.latest_execution.triggered_at) }}
                    </div>
                  </template>
                  <Tag v-else color="default">未执行</Tag>
                </template>
                <template v-else-if="column.key === 'action'">
                  <Button
                    size="small"
                    type="primary"
                    :loading="triggerLoading"
                    @click="handleTriggerClick(record as PipelineConfigRecord)"
                  >
                    触发
                  </Button>
                  <Button
                    size="small"
                    type="link"
                    @click="openEditConfig(record as PipelineConfigRecord)"
                  >
                    编辑
                  </Button>
                  <Button
                    size="small"
                    type="link"
                    @click="openConfigHistory(record as PipelineConfigRecord)"
                  >
                    历史
                  </Button>
                </template>
              </template>
            </Table>
          </Card>
        </TabPane>

        <TabPane key="templates" tab="测试模块模板">
          <Card :body-style="{ padding: 0 }">
            <div class="mb-3 flex items-center justify-between px-4 pt-3">
              <Segmented
                v-model:value="templateTypeFilter"
                :options="templateTypeOptions"
                @change="loadTemplates"
              />
              <Button type="primary" @click="openCreateTemplate">
                <template #icon><Plus class="size-4" /></template>
                新增模块
              </Button>
            </div>
            <Table
              :columns="templateColumns"
              :data-source="templates"
              :pagination="false"
              row-key="id"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'config'">
                  {{ templateConfig(record as TestModuleTemplateRecord) }}
                </template>
                <template v-else-if="column.key === 'split'">
                  <Tag
                    :color="
                      record.env_type === 'both'
                        ? 'orange'
                        : record.env_type === 'physical'
                          ? 'red'
                          : 'default'
                    "
                  >
                    {{ record.env_type }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'action'">
                  <Button
                    size="small"
                    type="link"
                    @click="
                      openEditTemplate(record as TestModuleTemplateRecord)
                    "
                  >
                    编辑
                  </Button>
                </template>
              </template>
            </Table>
          </Card>
        </TabPane>

        <TabPane key="runs" tab="近期执行">
          <Card :body-style="{ padding: 0 }">
            <Table
              :columns="executionColumns"
              :data-source="executions"
              :loading="runsLoading"
              :pagination="{ defaultPageSize: 20, showSizeChanger: true }"
              :scroll="{ x: 1300 }"
              row-key="id"
              size="small"
            >
              <template #bodyCell="{ column, record, text }">
                <template v-if="column.dataIndex === 'config_name'">
                  <span class="pipeline-cell-ellipsis">
                    {{ record.config_name }}
                  </span>
                </template>
                <template v-else-if="column.key === 'versions'">
                  <Tag
                    v-for="v in record.versions"
                    :key="v"
                    style="margin-bottom: 2px"
                  >
                    {{ v }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'archs'">
                  <Tag v-for="a in record.archs" :key="a" color="blue">
                    {{ a }}
                  </Tag>
                </template>
                <template v-else-if="column.dataIndex === 'status'">
                  <Tag :color="statusColor(record.status)">
                    {{ statusLabel(record.status) }}
                  </Tag>
                </template>
                <template
                  v-else-if="
                    ['triggered_at', 'completed_at'].includes(
                      String(column.dataIndex),
                    )
                  "
                >
                  {{ formatTime(text) }}
                </template>
                <template v-else-if="column.key === 'action'">
                  <Button
                    size="small"
                    type="link"
                    @click="openDetail(record as PipelineExecutionRecord)"
                  >
                    <template #icon><Eye class="size-4" /></template>
                    详情
                  </Button>
                </template>
              </template>
            </Table>
          </Card>
        </TabPane>
      </Tabs>
    </div>

    <!-- Config Modal -->
    <Modal
      v-model:open="configModalOpen"
      :title="editingConfig ? '编辑配置' : '创建 Pipeline 配置'"
      :width="
        configForm.pipeline_type === 'release'
          ? 'min(1100px, calc(100vw - 32px))'
          : '600px'
      "
      :confirm-loading="savingConfig"
      @ok="handleSaveConfig"
      @open-change="onConfigModalOpenChange"
    >
      <Form layout="vertical" class="space-y-2">
        <FormItem label="配置名称">
          <Input
            v-model:value="configForm.name"
            placeholder="如 openEuler Update Weekly"
          />
        </FormItem>
        <template v-if="configForm.pipeline_type === 'release'">
          <ReleaseConfigFields ref="releaseFields" :config="editingConfig" />
        </template>
        <template v-else>
          <div class="flex gap-4">
            <FormItem label="流水线类型（pipeline_type）" class="flex-1">
              <Select v-model:value="configForm.pipeline_type">
                <SelectOption
                  v-for="t in pipelineTypes"
                  :key="t.name"
                  :value="t.name"
                >
                  {{ t.name }}
                </SelectOption>
              </Select>
            </FormItem>
            <FormItem label="发行版（dist）" class="flex-1">
              <Input v-model:value="configForm.dist" disabled />
            </FormItem>
            <FormItem label="镜像轮次（image_round）" class="flex-1">
              <Input v-model:value="configForm.image_round" disabled />
            </FormItem>
          </div>
          <FormItem label="测试版本（可多选，也可手动输入新版本）">
            <Select
              v-model:value="configForm.versions"
              mode="tags"
              style="width: 100%"
              placeholder="选择或输入版本"
              @change="onVersionsChange"
            >
              <SelectOption v-for="v in versionOptions" :key="v" :value="v">
                {{ v }}
              </SelectOption>
            </Select>
          </FormItem>
          <FormItem label="测试架构">
            <Checkbox.Group v-model:value="configForm.archs">
              <Checkbox value="aarch64">aarch64</Checkbox>
              <Checkbox value="x86_64">x86_64</Checkbox>
            </Checkbox.Group>
            <div
              v-if="has64kVersion"
              style="
                margin-top: 4px;
                font-size: 12px;
                color: hsl(var(--muted-foreground));
              "
            >
              64k 版本仅支持 aarch64，x86_64 组合将自动跳过
            </div>
          </FormItem>
          <FormItem
            v-if="isDirectRunType(configForm.pipeline_type)"
            label="测试 Suite（可多选，也可手动输入新 Suite）"
          >
            <Select
              v-model:value="configForm.suites"
              mode="tags"
              style="width: 100%"
              :loading="mugenSuitesLoading"
              placeholder="选择或输入 Suite 名"
            >
              <SelectOption v-for="s in mugenSuites" :key="s" :value="s">
                {{ s }}
              </SelectOption>
            </Select>
          </FormItem>
          <FormItem v-else label="测试模块">
            <div class="flex flex-col gap-2">
              <Checkbox
                :checked="
                  configForm.pkgcmd_physical_enabled &&
                  configForm.pkgserver_physical_enabled &&
                  configForm.pkgunion_physical_enabled
                "
                @change="
                  (e: { target: { checked: boolean } }) => {
                    configForm.pkgcmd_physical_enabled = e.target.checked;
                    configForm.pkgserver_physical_enabled = e.target.checked;
                    configForm.pkgunion_physical_enabled = e.target.checked;
                  }
                "
              >
                执行物理机用例
              </Checkbox>
              <Checkbox.Group v-model:value="configForm.module_template_ids">
                <div class="flex flex-col gap-2">
                  <div
                    v-for="t in templates"
                    :key="t.id"
                    class="flex items-center gap-3"
                  >
                    <Checkbox :value="t.id">
                      {{ t.display_name }}
                      <span class="tmpl-suite">({{ t.suite_name }})</span>
                    </Checkbox>
                    <Switch
                      v-if="t.name === 'pkgcmd'"
                      v-model:checked="configForm.pkgcmd_physical_enabled"
                      size="small"
                    >
                      <template #checkedChildren>物理机</template>
                      <template #unCheckedChildren>仅 VM</template>
                    </Switch>
                    <Switch
                      v-else-if="t.name === 'pkgserver'"
                      v-model:checked="configForm.pkgserver_physical_enabled"
                      size="small"
                    >
                      <template #checkedChildren>物理机</template>
                      <template #unCheckedChildren>仅 VM</template>
                    </Switch>
                    <Switch
                      v-else-if="t.name === 'pkgunion'"
                      v-model:checked="configForm.pkgunion_physical_enabled"
                      size="small"
                    >
                      <template #checkedChildren>物理机</template>
                      <template #unCheckedChildren>仅 VM</template>
                    </Switch>
                  </div>
                </div>
              </Checkbox.Group>
            </div>
          </FormItem>
        </template>
      </Form>
    </Modal>

    <!-- Trigger Modal (direct_run types require trigger-level image_round) -->
    <Modal
      v-model:open="triggerModalOpen"
      :confirm-loading="triggerLoading"
      title="触发流水线"
      width="500px"
      @ok="handleTriggerConfirm"
    >
      <Form layout="vertical" class="space-y-2">
        <FormItem label="配置">
          <span>{{ triggerConfigLabel }}</span>
        </FormItem>
        <FormItem label="镜像轮次（image_round）" required>
          <Input
            v-model:value="triggerForm.image_round"
            placeholder="如 round-9（必填，本次触发对应的 RC 构建轮次）"
          />
        </FormItem>
      </Form>
    </Modal>

    <!-- Template Modal -->
    <Modal
      v-model:open="templateModalOpen"
      :title="editingTemplate ? '编辑模块模板' : '新增测试模块'"
      width="700px"
      :confirm-loading="savingTemplate"
      @ok="handleSaveTemplate"
    >
      <Form layout="vertical" class="space-y-2">
        <div class="flex gap-4">
          <FormItem label="模块标识（唯一）" class="flex-1">
            <Input
              v-model:value="templateForm.name"
              placeholder="如 docker"
              :disabled="!!editingTemplate"
            />
          </FormItem>
          <FormItem label="模块名称" class="flex-1">
            <Input
              v-model:value="templateForm.display_name"
              placeholder="如 Docker Update Test"
            />
          </FormItem>
        </div>
        <div class="flex gap-4">
          <FormItem label="Mugen Suite" class="flex-1">
            <Input
              v-model:value="templateForm.suite_name"
              placeholder="如 smoke"
            />
          </FormItem>
          <FormItem label="测试框架" class="flex-1">
            <Select v-model:value="templateForm.test_framework">
              <SelectOption value="mugen">mugen</SelectOption>
              <SelectOption value="ltp">ltp</SelectOption>
              <SelectOption value="other">other</SelectOption>
            </Select>
          </FormItem>
          <FormItem label="用例筛选策略" class="flex-1">
            <Select v-model:value="templateForm.case_filter">
              <SelectOption value="none">none（不筛选）</SelectOption>
              <SelectOption value="repodata_packages">
                repodata_packages（pkgcmd）
              </SelectOption>
              <SelectOption value="repodata_union">
                repodata_union（pkgunion）
              </SelectOption>
              <SelectOption value="service_test_cases">
                service_test_cases（pkgserver）
              </SelectOption>
            </Select>
          </FormItem>
        </div>
        <div class="flex gap-4">
          <FormItem label="环境套数（env_set_num）" class="flex-1">
            <InputNumber
              v-model:value="templateForm.env_set_num"
              :min="1"
              style="width: 100%"
            />
          </FormItem>
          <FormItem label="节点数（node_num）" class="flex-1">
            <InputNumber
              v-model:value="templateForm.node_num"
              :min="1"
              style="width: 100%"
            />
          </FormItem>
          <FormItem label="结果解析器" class="flex-1">
            <Select v-model:value="templateForm.result_parser">
              <SelectOption value="none">none</SelectOption>
              <SelectOption value="ltp">ltp</SelectOption>
              <SelectOption value="docker">docker</SelectOption>
              <SelectOption value="pkgcmd">pkgcmd</SelectOption>
              <SelectOption value="pkgmanage">pkgmanage</SelectOption>
              <SelectOption value="pkgserver">pkgserver</SelectOption>
              <SelectOption value="pkgunion">pkgunion</SelectOption>
            </Select>
          </FormItem>
        </div>
        <FormItem label="环境类型（env_type）">
          <Select v-model:value="templateForm.env_type">
            <SelectOption value="vm">vm（仅虚拟机）</SelectOption>
            <SelectOption value="physical">physical（仅物理机）</SelectOption>
            <SelectOption value="both">both（VM+物理机都跑）</SelectOption>
          </Select>
        </FormItem>
        <FormItem
          label="mugen_exec_command（自定义 Mugen 执行命令，留空则用默认）"
        >
          <Textarea
            v-model:value="templateForm.mugen_exec_command"
            :rows="3"
            placeholder="留空使用默认：cd /opt/mugen && mugen.sh -f {suite} -r {case} -x&#10;docker 模块示例：docker exec openEuler_test bash -c 'cd /home/mugen && mugen.sh -f {suite} -r {case} -x'"
            style="font-family: monospace; font-size: 12px"
          />
        </FormItem>
        <FormItem label="pre_env_script（环境准备脚本）">
          <Textarea
            v-model:value="templateForm.pre_env_script"
            :rows="6"
            placeholder="#!/bin/bash&#10;# VM 启动后、Mugen 执行前运行的脚本&#10;# 可用环境变量：KRONOS_OS_VERSION, KRONOS_ARCH, KRONOS_ENV_SET_INDEX, OET_PATH（mugen 目录，默认 /opt/mugen）"
            style="font-family: monospace; font-size: 12px"
          />
        </FormItem>
        <FormItem label="rerun_env_script（重跑局部准备脚本）">
          <Textarea
            v-model:value="templateForm.rerun_env_script"
            :rows="5"
            placeholder="# 每个复用环境套在重跑用例前执行一次；首次执行不运行"
            style="font-family: monospace; font-size: 12px"
          />
        </FormItem>
        <FormItem label="post_env_script（结果整理脚本）">
          <Textarea
            v-model:value="templateForm.post_env_script"
            :rows="6"
            placeholder="#!/bin/bash&#10;# Mugen 执行后、日志收集前运行的脚本&#10;# 可用环境变量：KRONOS_OS_VERSION, KRONOS_ARCH, KRONOS_ENV_SET_INDEX, OET_PATH（mugen 目录，默认 /opt/mugen）&#10;# mugen 日志在 ${OET_PATH}/logs/，结果在 ${OET_PATH}/results/"
            style="font-family: monospace; font-size: 12px"
          />
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.tmpl-suite {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.pipeline-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
}

.pipeline-toolbar__left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.pipeline-toolbar__right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.pipeline-cell-muted {
  font-size: 12px;
}

.pipeline-cell-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
