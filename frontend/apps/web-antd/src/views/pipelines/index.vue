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
