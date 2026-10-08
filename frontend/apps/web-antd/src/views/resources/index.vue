<script lang="ts" setup>
import type {
  TableColumnsType,
  TablePaginationConfig,
  UploadFile,
  UploadProps,
} from 'ant-design-vue';
import type { Dayjs } from 'dayjs';

import type { ResourceFilterKey } from './resources-view';

import type {
  PhysicalInstallImage,
  ResourceCreatePayload,
  ResourceCredentialRecord,
  ResourceImportResult,
  ResourceImportRowResult,
  ResourceListParams,
  ResourceMatchMode,
  ResourceRecord,
  ResourceUpdatePayload,
  UserRole,
} from '#/api';

import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import {
  Download,
  Eye,
  Inbox,
  LogOut,
  Plus,
  RotateCw,
  UserRoundPen,
} from '@vben/icons';
import { useUserStore } from '@vben/stores';

import {
  Switch as AntSwitch,
  Button,
  Card,
  Checkbox,
  DatePicker,
  Descriptions,
  DescriptionsItem,
  Drawer,
  Form,
  FormItem,
  Input,
  InputNumber,
  message,
  Modal,
  RadioButton,
  RadioGroup,
  Select,
  Space,
  Table,
  Tag,
  Upload,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  createResourceApi,
  exportResourcesCsvApi,
  extendLeaseApi,
  forceReleaseLeaseApi,
  getResourceApi,
  getResourceCredentialsApi,
  getResourcesApi,
  importLeasesCsvApi,
  importResourcesCsvApi,
  installResourceApi,
  listInstallBaseVariantsApi,
  listInstallImagesApi,
  occupyResourceApi,
  probeResourceApi,
  releaseLeaseApi,
  updateInstallBaseVariantApi,
  updateResourceApi,
} from '#/api';

import {
  createIdempotencyAttempt,
  idempotencyKeyFor,
  resetIdempotencyAttempt,
} from '../_shared/idempotency';
import { createLatestRequestGuard } from '../_shared/latest-request';
import ManagementFilterPanel from '../_shared/management-filter-panel.vue';
import { tablePagination } from '../_shared/table-pagination';
import {
  buildResourceListParams,
  canForceReleaseResource,
  canUseResourceDestructiveActions,
  resourceFilterItems,
  resourceTestStatusLabel,
} from './resources-view';

type FilterKey = ResourceFilterKey;
type ImportTarget = 'leases' | 'resources';

const route = useRoute();
const router = useRouter();
const resourceListRequest = createLatestRequestGuard();

interface ValidatableForm {
  validate: () => Promise<void>;
}

const loading = ref(false);
const leaseOpen = ref(false);
const leaseSubmitting = ref(false);
const renewOpen = ref(false);
const renewSubmitting = ref(false);
const editOpen = ref(false);
const editSubmitting = ref(false);
const credentialLoading = ref(false);
const showAll = ref(false);
const importOpen = ref(false);
const importPreviewing = ref(false);
const importSubmitting = ref(false);
const exportSubmitting = ref(false);
const importFile = ref<File | null>(null);
const importResult = ref<null | ResourceImportResult>(null);
const importTarget = ref<ImportTarget>('resources');
const resources = ref<ResourceRecord[]>([]);
const resourcePage = ref(1);
const resourceTotal = ref(0);
const selectedResource = ref<null | ResourceRecord>(null);
const editTarget = ref<null | ResourceRecord>(null);
const leaseTarget = ref<null | ResourceRecord>(null);
const renewTarget = ref<null | ResourceRecord>(null);
const credentials = ref<null | ResourceCredentialRecord>(null);
const detailOpen = ref(false);
let credentialRequestToken = 0;
const leaseIdempotency = createIdempotencyAttempt();
const renewIdempotency = createIdempotencyAttempt();
const importIdempotency = createIdempotencyAttempt();
const editFormRef = ref<null | ValidatableForm>(null);
const editMode = ref<'create' | 'edit'>('edit');
const matchMode = ref<ResourceMatchMode>('and');
const userStore = useUserStore();
const filters = reactive<Record<FilterKey, string>>({
  arch: '',
  bmc_ip: '',
  cpu_model: '',
  current_lease_purpose: '',
  current_lease_username: '',
  kernel_version: '',
  mac_address: '',
  management_status: '',
  name: '',
  occupancy_status: '',
  os_version: '',
  primary_ip: '',
  resource_code: '',
  resource_type: '',
  usage_scenario: '',
});
const leaseForm = reactive({
  expectedEndsAt: dayjs().add(1, 'day') as Dayjs | undefined,
  permanent: false,
  purpose: '',
});
const renewForm = reactive({
  expectedEndsAt: dayjs().add(1, 'day') as Dayjs | undefined,
});
const editForm = reactive({
  arch: '',
  bmc_password: '',
  bmc_ip: '',
  bmc_username: '',
  board_sn: '',
  connectivity_status: 'unknown' as ResourceRecord['connectivity_status'],
  cpu_count: undefined as number | undefined,
  cpu_model: '',
  device_distribution: '',
  device_location: '',
  extra: '',
  hdd_count: undefined as number | undefined,
  hdd_spec: '',
  is_critical: false,
  kernel_version: '',
  mac_address: '',
  management_status: 'active' as ResourceRecord['management_status'],
  memory_count: undefined as number | undefined,
  memory_spec: '',
  name: '',
  os_version: '',
  primary_ip: '',
  resource_code: '',
  ssh_password: '',
  ssh_username: '',
  ssd_card_count: undefined as number | undefined,
  ssd_card_spec: '',
  ssd_count: undefined as number | undefined,
  ssd_spec: '',
  tags: '',
  usage_scenario: '',
});

const managementStatusOptions: Array<{
  label: string;
  value: ResourceRecord['management_status'];
}> = [
  { label: 'active', value: 'active' },
  { label: 'maintenance', value: 'maintenance' },
  { label: 'disabled', value: 'disabled' },
];
const connectivityStatusOptions: Array<{
  label: string;
  value: ResourceRecord['connectivity_status'];
}> = [
  { label: 'unknown', value: 'unknown' },
  { label: 'reachable', value: 'reachable' },
  { label: 'unreachable', value: 'unreachable' },
];

const filterItems = resourceFilterItems;

const columns: TableColumnsType<ResourceRecord> = [
  {
    dataIndex: 'primary_ip',
    fixed: 'left',
    title: 'OS IP',
    width: 150,
  },
  {
    dataIndex: 'name',
    ellipsis: true,
    title: '显示名',
    width: 160,
  },
  {
    dataIndex: 'management_status',
    title: '管理状态',
    width: 110,
  },
  {
    dataIndex: 'occupancy_status',
    title: '占用状态',
    width: 90,
  },
  {
    dataIndex: 'test_status',
    title: '测试状态',
    width: 150,
  },
  {
    dataIndex: 'current_lease_username',
    title: '占用人',
    width: 100,
  },
  {
    dataIndex: 'current_lease_purpose',
    ellipsis: true,
    title: '占用用途',
    width: 150,
  },
  {
    dataIndex: 'current_lease_expected_ends_at',
    title: '占用到',
    width: 150,
  },
  {
    dataIndex: 'usage_scenario',
    ellipsis: true,
    title: '使用场景',
    width: 130,
  },
  {
    dataIndex: 'bmc_ip',
    title: 'BMC IP',
    width: 130,
  },
  {
    dataIndex: 'arch',
    title: '架构',
    width: 80,
  },
  {
    dataIndex: 'tags',
    title: '标签',
    width: 180,
  },
  {
    fixed: 'right',
    key: 'action',
    title: '',
    width: 360,
  },
];

const importResultColumns: TableColumnsType<ResourceImportRowResult> = [
  {
    dataIndex: 'row_number',
    title: '行号',
    width: 72,
  },
  {
    dataIndex: 'resource_code',
    ellipsis: true,
    title: '资源编码',
    width: 180,
  },
  {
    dataIndex: 'primary_ip',
    title: 'OS IP',
    width: 140,
  },
  {
    dataIndex: 'status',
    title: '状态',
    width: 96,
  },
  {
    dataIndex: 'errors',
    ellipsis: true,
    title: '错误',
  },
];

const activeFilterCount = computed(
  () => Object.values(filters).filter((value) => value.trim()).length,
);
const importFileList = computed<UploadFile[]>(() =>
  importFile.value
    ? [
        {
          name: importFile.value.name,
          status: 'done',
          uid: 'resource-import-file',
        },
      ]
    : [],
);
const currentUserId = computed(() => userStore.userInfo?.userId);
const currentUsername = computed(() => userStore.userInfo?.username);
const currentRole = computed(
  () => userStore.userInfo?.roles?.[0] as undefined | UserRole,
);
const isAdmin = computed(() => currentRole.value === 'ADMIN');
const isCreatingResource = computed(() => editMode.value === 'create');

function buildParams(): ResourceListParams {
  return buildResourceListParams({
    currentUsername: currentUsername.value,
    filters,
    matchMode: matchMode.value,
    page: resourcePage.value,
    showAll: showAll.value,
  });
}

async function loadResources() {
  const request = resourceListRequest.begin();
  loading.value = true;
  try {
    const response = await getResourcesApi(buildParams());
    request.commit(() => {
      resources.value = response.items;
      resourceTotal.value = response.total;
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function exportResources() {
  exportSubmitting.value = true;
  try {
    const blob = await exportResourcesCsvApi(buildParams());
    downloadBlob(blob, 'radiaTest-resources.csv');
    message.success('资源已导出');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '资源导出失败');
  } finally {
    exportSubmitting.value = false;
  }
}

function resetFilters() {
  for (const key of Object.keys(filters) as FilterKey[]) {
    filters[key] = '';
  }
  matchMode.value = 'and';
  resourcePage.value = 1;
  void loadResources();
}

function searchResources() {
  resourcePage.value = 1;
  void loadResources();
}

function changePage(pagination: TablePaginationConfig) {
  resourcePage.value = pagination.current ?? 1;
  void loadResources();
}

function openImportModal() {
  importFile.value = null;
  importResult.value = null;
  importTarget.value = 'resources';
  importOpen.value = true;
}

const beforeImportFile: UploadProps['beforeUpload'] = (file) => {
  resetIdempotencyAttempt(importIdempotency);
  importFile.value = file as File;
  importResult.value = null;
  return false;
};

function removeImportFile() {
  resetIdempotencyAttempt(importIdempotency);
  importFile.value = null;
  importResult.value = null;
  return true;
}

async function loadCredentialsForDetail(resource: ResourceRecord) {
  const requestToken = ++credentialRequestToken;
  credentials.value = null;
  credentialLoading.value = false;
  if (!canViewCredentials(resource)) {
    return;
  }
  credentialLoading.value = true;
  try {
    const loadedCredentials = await getResourceCredentialsApi(resource.id);
    if (
      requestToken === credentialRequestToken &&
      detailOpen.value &&
      selectedResource.value?.id === resource.id
    ) {
      credentials.value = loadedCredentials;
    }
  } catch {
    if (requestToken === credentialRequestToken) {
      credentials.value = null;
    }
  } finally {
    if (requestToken === credentialRequestToken) {
      credentialLoading.value = false;
    }
  }
}

function clearDetailCredentials() {
  credentialRequestToken += 1;
  credentials.value = null;
  credentialLoading.value = false;
}

function openDetail(resource: ResourceRecord) {
  selectedResource.value = resource;
  detailOpen.value = true;
  void loadCredentialsForDetail(resource);
}

function openTableDetail(record: Record<string, unknown>) {
  openDetail(record as unknown as ResourceRecord);
}

watch(detailOpen, (open) => {
  if (!open) clearDetailCredentials();
});

async function openRequestedResource(resourceId: string) {
  showAll.value = true;
  const target = await getResourceApi(resourceId).catch(() => null);
  await router.replace('/resources');
  if (target?.resource_type === 'PHYSICAL') {
    openDetail(target);
  } else {
    message.warning('物理机不存在或已不可用');
  }
}

function asResourceRecord(record: Record<string, unknown>) {
  return record as unknown as ResourceRecord;
}

function statusColor(status: string) {
  if (status === 'active' || status === 'idle' || status === 'reachable') {
    return 'green';
  }
  if (status === 'unknown') {
    return 'default';
  }
  if (status === 'maintenance') {
    return 'orange';
  }
  if (status === 'testing') {
    return 'blue';
  }
  return 'red';
}

function importStatusColor(status: string) {
  if (status === 'created' || status === 'validated') {
    return 'green';
  }
  return 'red';
}

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function displayValue(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function credentialValue(hasPassword: boolean, value?: null | string) {
  if (!hasPassword) return '未保存';
  if (!selectedResource.value || !canViewCredentials(selectedResource.value)) {
    return '***';
  }
  if (credentialLoading.value) return '加载中...';
  return value || '***';
}

function normalizeOptional(value: string) {
  const trimmed = value.trim();
  return trimmed || null;
}

function tagsToText(tags: string[]) {
  return tags.join(', ');
}

function parseTags(value: string) {
  const tags = value
    .split(/[\s,，]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
  return [...new Set(tags)];
}

function parseExtraJson(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('extra must be an object');
  }
  return parsed as Record<string, unknown>;
}

function canEdit(record: ResourceRecord) {
  return isAdmin.value && record.resource_type === 'PHYSICAL';
}

function canInstall(record: ResourceRecord) {
  return (
    isAdmin.value &&
    record.resource_type === 'PHYSICAL' &&
    Boolean(record.bmc_ip) &&
    Boolean(record.mac_address) &&
    Boolean(record.primary_ip) &&
    record.management_status !== 'maintenance'
  );
}

function canProbe(record: ResourceRecord) {
  return (
    isAdmin.value &&
    record.resource_type === 'PHYSICAL' &&
    Boolean(record.primary_ip)
  );
}

function canOccupy(record: ResourceRecord) {
  if (
    record.management_status !== 'active' ||
    record.occupancy_status !== 'idle'
  ) {
    return false;
  }
  return !record.is_critical || isAdmin.value;
}

function canRelease(record: ResourceRecord) {
  return Boolean(
    record.current_lease_id &&
    record.current_lease_user_id === currentUserId.value,
  );
}

function canRenew(record: ResourceRecord) {
  if (
    !record.current_lease_id ||
    !record.current_lease_expected_ends_at ||
    record.current_lease_user_id !== currentUserId.value
  ) {
    return false;
  }
  return dayjs(record.current_lease_expected_ends_at).isBefore(
    dayjs().add(7, 'day'),
  );
}

const installImages = ref<PhysicalInstallImage[]>([]);
const installBaseVariants = ref<Record<string, string>>({});
const installBaseDrafts = ref<Record<string, string>>({});
const installBaseSaving = ref(false);
const installModalVisible = ref(false);
const installTargetResourceId = ref('');
const installTargetArch = ref('');
const installSelectedOsVersion = ref('');
const installSelectedRound = ref('');
const installSelectedKernel = ref('');
const installing = ref(false);
const probing = ref(false);
// 只列出"有安装源"的镜像（repo_url 已由本地登记回填）；源缺失的行不可装。
const installImagesFiltered = computed(() =>
  installTargetArch.value
    ? installImages.value.filter(
        (img) => img.arch === installTargetArch.value && img.repo_url,
      )
    : installImages.value.filter((img) => img.repo_url),
);
// 版本按发行版前缀分组（openEuler-26.09 / openEuler-24.03-LTS）
const installOsVersionGroups = computed(() => {
  const groups: Record<string, { label: string; value: string }[]> = {};
  for (const img of installImagesFiltered.value) {
    const parts = img.os_version.split('-');
    const prefix =
      parts.length >= 3 ? parts.slice(0, 3).join('-') : img.os_version;
    (groups[prefix] ??= []).push({
      label: img.os_version,
      value: img.os_version,
    });
  }
  return Object.entries(groups).map(([prefix, items]) => ({
    label: prefix,
    options: items.filter(
      (v, i, a) => a.findIndex((x) => x.value === v.value) === i,
    ),
  }));
});
// 轮次选项（选版本后该 os_version+arch 的 round）
const installRoundOptions = computed(() => {
  if (!installSelectedOsVersion.value) return [];
  const rounds = installImagesFiltered.value
    .filter((img) => img.os_version === installSelectedOsVersion.value)
    .map((img) => img.round || 'official');
  return [...new Set(rounds)].map((r) => ({ label: r, value: r }));
});
// 内核变体选项（选版本+轮次后）；徽标区分直装 / 基础+换内核
const installKernelOptions = computed(() => {
  if (!installSelectedOsVersion.value || !installSelectedRound.value) return [];
  const kernels = installImagesFiltered.value.filter(
    (img) =>
      img.os_version === installSelectedOsVersion.value &&
      (img.round || 'official') === installSelectedRound.value,
  );
  return kernels.map((img) => {
    const base = installBaseVariants.value[img.os_version] || '?';
    const badge = img.swap_kernel_variant ? `[装${base}+换内核]` : '[本地直装]';
    return {
      label: img.kernel_variant
        ? `${img.kernel_variant} 内核 ${badge}`
        : `默认内核 ${badge}`,
      value: img.kernel_variant || '',
    };
  });
});
// 最终 image id（从三级选 + arch 找）
const installSelectedImageId = computed(() => {
  const img = installImagesFiltered.value.find(
    (img) =>
      img.os_version === installSelectedOsVersion.value &&
      (img.round || 'official') === installSelectedRound.value &&
      (img.kernel_variant || '') === installSelectedKernel.value,
  );
  return img?.id || '';
});

function openInstallModal(record: ResourceRecord) {
  installTargetResourceId.value = record.id;
  installTargetArch.value = record.arch ?? '';
  installSelectedOsVersion.value = '';
  installSelectedRound.value = '';
  installSelectedKernel.value = '';
  installModalVisible.value = true;
  if (isAdmin.value && installImages.value.length === 0) {
    void listInstallImagesApi()
      .then((images) => {
        installImages.value = images ?? [];
      })
      .catch(() => {});
  }
  if (Object.keys(installBaseVariants.value).length === 0) {
    void listInstallBaseVariantsApi()
      .then((rows) => {
        installBaseVariants.value = Object.fromEntries(
          (rows ?? []).map((r) => [r.os_version, r.base_kernel_variant]),
        );
        installBaseDrafts.value = { ...installBaseVariants.value };
      })
      .catch(() => {});
  }
}

async function handleInstall() {
  if (!installSelectedImageId.value) {
    message.warning('请选择安装镜像');
    return;
  }
  installing.value = true;
  try {
    const res = await installResourceApi(
      installTargetResourceId.value,
      installSelectedImageId.value,
      `install-${installTargetResourceId.value}-${Date.now()}`,
    );
    message.success(`装机任务已提交，任务 ID: ${res.task_id}`);
    installModalVisible.value = false;
  } catch {
    message.error('提交装机任务失败');
  } finally {
    installing.value = false;
  }
}

async function saveInstallBaseVariant(osVersion: string) {
  installBaseSaving.value = true;
  try {
    await updateInstallBaseVariantApi(
      osVersion,
      installBaseDrafts.value[osVersion] || '',
    );
    installBaseVariants.value[osVersion] =
      installBaseDrafts.value[osVersion] || '';
    message.success(`已保存 ${osVersion} 基础内核`);
  } catch {
    message.error('保存基础内核配置失败');
  } finally {
    installBaseSaving.value = false;
  }
}

async function probeHardware(record: ResourceRecord) {
  probing.value = true;
  try {
    const res = await probeResourceApi(record.id);
    message.success(`硬件信息已刷新（${res.fields_updated.length} 项）`);
    const updated = await getResourceApi(record.id);
    openDetail(updated);
  } catch {
    message.error('硬件探测失败');
  } finally {
    probing.value = false;
  }
}

function canForceRelease(record: ResourceRecord) {
  return canForceReleaseResource(record, {
    currentRole: currentRole.value,
    currentUserId: currentUserId.value,
  });
}

function canViewCredentials(record: ResourceRecord) {
  if (!record.has_ssh_password && !record.has_bmc_password) {
    return false;
  }
  if (isAdmin.value) {
    return true;
  }
  return (
    !record.is_critical && record.current_lease_user_id === currentUserId.value
  );
}

function resetEditForm() {
  editForm.resource_code = '';
  editForm.name = '';
  editForm.management_status = 'active';
  editForm.connectivity_status = 'unknown';
  editForm.is_critical = false;
  editForm.primary_ip = '';
  editForm.mac_address = '';
  editForm.bmc_ip = '';
  editForm.bmc_username = '';
  editForm.bmc_password = '';
  editForm.ssh_username = '';
  editForm.ssh_password = '';
  editForm.arch = '';
  editForm.os_version = '';
  editForm.kernel_version = '';
  editForm.cpu_model = '';
  editForm.cpu_count = undefined;
  editForm.memory_count = undefined;
  editForm.memory_spec = '';
  editForm.hdd_count = undefined;
  editForm.hdd_spec = '';
  editForm.ssd_count = undefined;
  editForm.ssd_spec = '';
  editForm.ssd_card_count = undefined;
  editForm.ssd_card_spec = '';
  editForm.board_sn = '';
  editForm.device_location = '';
  editForm.device_distribution = '';
  editForm.usage_scenario = '';
  editForm.tags = '';
  editForm.extra = '{}';
}

function openCreateModal() {
  editMode.value = 'create';
  editTarget.value = null;
  resetEditForm();
  editOpen.value = true;
}

function openEditModal(record: ResourceRecord) {
  editMode.value = 'edit';
  editTarget.value = record;
  resetEditForm();
  editForm.resource_code = record.resource_code;
  editForm.name = record.name ?? '';
  editForm.management_status = record.management_status;
  editForm.connectivity_status = record.connectivity_status;
  editForm.is_critical = record.is_critical;
  editForm.primary_ip = record.primary_ip ?? '';
  editForm.mac_address = record.mac_address ?? '';
  editForm.bmc_ip = record.bmc_ip ?? '';
  editForm.bmc_username = record.bmc_username ?? '';
  editForm.ssh_username = record.ssh_username;
  editForm.arch = record.arch ?? '';
  editForm.os_version = record.os_version ?? '';
  editForm.kernel_version = record.kernel_version ?? '';
  editForm.cpu_model = record.cpu_model ?? '';
  editForm.cpu_count = record.cpu_count ?? undefined;
  editForm.memory_count = record.memory_count ?? undefined;
  editForm.memory_spec = record.memory_spec ?? '';
  editForm.hdd_count = record.hdd_count ?? undefined;
  editForm.hdd_spec = record.hdd_spec ?? '';
  editForm.ssd_count = record.ssd_count ?? undefined;
  editForm.ssd_spec = record.ssd_spec ?? '';
  editForm.ssd_card_count = record.ssd_card_count ?? undefined;
  editForm.ssd_card_spec = record.ssd_card_spec ?? '';
  editForm.board_sn = record.board_sn ?? '';
  editForm.device_location = record.device_location ?? '';
  editForm.device_distribution = record.device_distribution ?? '';
  editForm.usage_scenario = record.usage_scenario ?? '';
  editForm.tags = tagsToText(record.tags);
  editForm.extra = JSON.stringify(record.extra ?? {}, null, 2);
  editOpen.value = true;
}

async function submitEditResource() {
  const target = editTarget.value;
  if (!isCreatingResource.value && !target) return;
  await editFormRef.value?.validate();
  let extra: Record<string, unknown>;
  try {
    extra = parseExtraJson(editForm.extra);
  } catch {
    message.warning('扩展 JSON 必须是对象');
    return;
  }

  const payload: ResourceUpdatePayload = {
    arch: normalizeOptional(editForm.arch),
    bmc_ip: normalizeOptional(editForm.bmc_ip),
    bmc_username: normalizeOptional(editForm.bmc_username),
    board_sn: normalizeOptional(editForm.board_sn),
    connectivity_status: editForm.connectivity_status,
    cpu_count: editForm.cpu_count ?? null,
    cpu_model: normalizeOptional(editForm.cpu_model),
    device_distribution: normalizeOptional(editForm.device_distribution),
    device_location: normalizeOptional(editForm.device_location),
    extra,
    hdd_count: editForm.hdd_count ?? null,
    hdd_spec: normalizeOptional(editForm.hdd_spec),
    is_critical: editForm.is_critical,
    kernel_version: normalizeOptional(editForm.kernel_version),
    mac_address: normalizeOptional(editForm.mac_address),
    management_status: editForm.management_status,
    memory_count: editForm.memory_count ?? null,
    memory_spec: normalizeOptional(editForm.memory_spec),
    name: normalizeOptional(editForm.name),
    os_version: normalizeOptional(editForm.os_version),
    primary_ip: editForm.primary_ip.trim(),
    ssh_username: editForm.ssh_username.trim(),
    ssd_card_count: editForm.ssd_card_count ?? null,
    ssd_card_spec: normalizeOptional(editForm.ssd_card_spec),
    ssd_count: editForm.ssd_count ?? null,
    ssd_spec: normalizeOptional(editForm.ssd_spec),
    tags: parseTags(editForm.tags),
    usage_scenario: normalizeOptional(editForm.usage_scenario),
  };
  const sshPassword = editForm.ssh_password.trim();
  const bmcPassword = editForm.bmc_password.trim();
  if (isCreatingResource.value) {
    if (!sshPassword || !bmcPassword) {
      message.warning('请填写 SSH/BMC 密码');
      return;
    }
  } else {
    if (sshPassword) {
      payload.ssh_password = sshPassword;
    }
    if (bmcPassword) {
      payload.bmc_password = bmcPassword;
    }
  }

  editSubmitting.value = true;
  try {
    let updated: ResourceRecord;
    if (isCreatingResource.value) {
      const createPayload: ResourceCreatePayload = {
        ...payload,
        bmc_ip: editForm.bmc_ip.trim(),
        bmc_password: bmcPassword,
        bmc_username: editForm.bmc_username.trim(),
        primary_ip: editForm.primary_ip.trim(),
        resource_code: editForm.resource_code.trim(),
        resource_type: 'PHYSICAL',
        ssh_password: sshPassword,
        ssh_username: editForm.ssh_username.trim(),
      };
      updated = await createResourceApi(createPayload);
    } else {
      if (!target) return;
      updated = await updateResourceApi(target.id, payload);
    }
    message.success(isCreatingResource.value ? '资源已创建' : '资源已更新');
    editOpen.value = false;
    if (!isCreatingResource.value) {
      selectedResource.value =
        selectedResource.value?.id === updated.id
          ? updated
          : selectedResource.value;
    }
    await loadResources();
  } finally {
    editSubmitting.value = false;
  }
}

function openLeaseModal(record: ResourceRecord) {
  leaseTarget.value = record;
  leaseForm.purpose = record.usage_scenario ?? '';
  leaseForm.permanent = isAdmin.value;
  leaseForm.expectedEndsAt = isAdmin.value ? undefined : dayjs().add(1, 'day');
  leaseOpen.value = true;
}

function disabledLeaseDate(current: Dayjs) {
  if (!current) return false;
  if (current.isBefore(dayjs().startOf('day'))) {
    return true;
  }
  if (isAdmin.value) {
    return false;
  }
  return current.isAfter(dayjs().add(14, 'day').endOf('day'));
}

function disabledRenewDate(current: Dayjs) {
  if (!current) return false;
  if (current.isBefore(dayjs().startOf('day'))) {
    return true;
  }
  return current.isAfter(dayjs().add(7, 'day').endOf('day'));
}

async function submitLease() {
  if (!leaseTarget.value) return;
  const purpose = leaseForm.purpose.trim();
  if (!purpose) {
    message.warning('请填写占用用途');
    return;
  }
  if (!isAdmin.value && !leaseForm.expectedEndsAt) {
    message.warning('请选择占用截止时间');
    return;
  }

  const payload = {
    expected_ends_at:
      isAdmin.value && leaseForm.permanent
        ? null
        : leaseForm.expectedEndsAt?.toISOString(),
    purpose,
  };
  leaseSubmitting.value = true;
  try {
    await occupyResourceApi(
      leaseTarget.value.id,
      payload,
      idempotencyKeyFor(leaseIdempotency, 'occupy', {
        resourceId: leaseTarget.value.id,
        ...payload,
      }),
    );
    resetIdempotencyAttempt(leaseIdempotency);
    message.success('资源已占用');
    leaseOpen.value = false;
    await loadResources();
  } finally {
    leaseSubmitting.value = false;
  }
}

function openRenewModal(record: ResourceRecord) {
  if (!record.current_lease_expected_ends_at) return;
  renewTarget.value = record;
  const currentEnd = dayjs(record.current_lease_expected_ends_at);
  const maxEnd = dayjs().add(7, 'day').add(1, 'minute');
  const nextEnd = currentEnd.add(1, 'day');
  renewForm.expectedEndsAt = nextEnd.isAfter(maxEnd) ? maxEnd : nextEnd;
  renewOpen.value = true;
}

async function submitRenew() {
  if (!renewTarget.value?.current_lease_id) return;
  const currentEndsAt = renewTarget.value.current_lease_expected_ends_at;
  if (!currentEndsAt) return;
  if (!renewForm.expectedEndsAt) {
    message.warning('请选择续期截止时间');
    return;
  }
  const currentEnd = dayjs(currentEndsAt);
  const maxEnd = dayjs().add(7, 'day').add(1, 'minute');
  if (!renewForm.expectedEndsAt.isAfter(dayjs())) {
    message.warning('续期截止时间必须晚于当前时间');
    return;
  }
  if (!renewForm.expectedEndsAt.isAfter(currentEnd)) {
    message.warning('续期截止时间必须晚于当前租约截止时间');
    return;
  }
  if (renewForm.expectedEndsAt.isAfter(maxEnd)) {
    message.warning('续期截止时间不能超过当前时间 7 天后');
    return;
  }

  const payload = { expected_ends_at: renewForm.expectedEndsAt.toISOString() };
  renewSubmitting.value = true;
  try {
    await extendLeaseApi(
      renewTarget.value.current_lease_id,
      payload,
      idempotencyKeyFor(renewIdempotency, 'extend', {
        leaseId: renewTarget.value.current_lease_id,
        ...payload,
      }),
    );
    resetIdempotencyAttempt(renewIdempotency);
    message.success('租约已续期');
    renewOpen.value = false;
    await loadResources();
  } finally {
    renewSubmitting.value = false;
  }
}

function releaseResource(record: ResourceRecord, force = false) {
  if (!record.current_lease_id) return;
  const payload = { reason: force ? '强制释放' : '用户释放' };
  const idempotencyKey = idempotencyKeyFor(
    createIdempotencyAttempt(),
    force ? 'force-release' : 'release',
    { leaseId: record.current_lease_id, ...payload },
  );
  Modal.confirm({
    content: force
      ? `确认强制释放 ${record.primary_ip}？`
      : `确认释放 ${record.primary_ip}？`,
    okText: force ? '强制释放' : '释放',
    onOk: async () => {
      const api = force ? forceReleaseLeaseApi : releaseLeaseApi;
      await api(record.current_lease_id as string, payload, idempotencyKey);
      message.success(force ? '资源已强制释放' : '资源已释放');
      detailOpen.value = false;
      await loadResources();
    },
    title: force ? '强制释放资源' : '释放资源',
  });
}

watch(importTarget, () => {
  resetIdempotencyAttempt(importIdempotency);
  importResult.value = null;
});

watch(showAll, () => {
  resourcePage.value = 1;
  void loadResources();
});

watch(
  () => route.query.resource_id,
  (resourceId) => {
    if (typeof resourceId === 'string') void openRequestedResource(resourceId);
  },
);

async function buildImportPayload(dryRun: boolean) {
  if (!importFile.value) {
    message.warning('请选择 CSV 文件');
    return null;
  }
  if (!importFile.value.name.toLowerCase().endsWith('.csv')) {
    message.warning('请选择 CSV 文件');
    return null;
  }
  return {
    content: await importFile.value.text(),
    dry_run: dryRun,
    filename: importFile.value.name,
  };
}

async function previewCsvImport() {
  const payload = await buildImportPayload(true);
  if (!payload) return;
  importPreviewing.value = true;
  try {
    importResult.value =
      importTarget.value === 'resources'
        ? await importResourcesCsvApi(payload)
        : await importLeasesCsvApi(payload);
    if (importResult.value.error_count > 0) {
      message.warning('校验完成，请处理错误行');
    } else {
      message.success('校验通过');
    }
  } finally {
    importPreviewing.value = false;
  }
}

async function submitCsvImport() {
  const payload = await buildImportPayload(false);
  if (!payload) return;
  importSubmitting.value = true;
  try {
    const idempotencyKey = idempotencyKeyFor(
      importIdempotency,
      importTarget.value === 'resources' ? 'resource-import' : 'lease-import',
      {
        fileLastModified: importFile.value?.lastModified,
        fileName: importFile.value?.name,
        fileSize: importFile.value?.size,
        target: importTarget.value,
      },
    );
    importResult.value =
      importTarget.value === 'resources'
        ? await importResourcesCsvApi(payload, idempotencyKey)
        : await importLeasesCsvApi(payload, idempotencyKey);
    if (importResult.value.success_count > 0) {
      resetIdempotencyAttempt(importIdempotency);
      message.success(`已导入 ${importResult.value.success_count} 行`);
      await loadResources();
    }
    if (importResult.value.error_count > 0) {
      message.warning('部分行导入失败');
    }
  } finally {
    importSubmitting.value = false;
  }
}

onMounted(async () => {
  const requestedResourceId =
    typeof route.query.resource_id === 'string'
      ? route.query.resource_id
      : null;
  if (requestedResourceId) showAll.value = true;
  await loadResources();
  if (!requestedResourceId) return;
  await openRequestedResource(requestedResourceId);
});
</script>

<template>
  <Page title="物理机管理">
    <div class="space-y-4">
      <ManagementFilterPanel
        :active-filter-count="activeFilterCount"
        :loading="loading"
        @reset="resetFilters"
        @search="searchResources"
      >
        <div
          v-for="item in filterItems"
          :key="item.key"
          class="management-filter__field"
        >
          <span class="management-filter__label">{{ item.label }}</span>
          <Input
            v-model:value="filters[item.key]"
            allow-clear
            size="small"
            @press-enter="searchResources"
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
          <Button size="small" @click="showAll = !showAll">
            {{ showAll ? '我的占用' : '查看全部' }}
          </Button>
        </template>
      </ManagementFilterPanel>

      <Card class="management-table-card" :body-style="{ padding: 0 }">
        <div class="management-toolbar management-toolbar--table">
          <div class="management-toolbar__group">
            <span>物理机列表</span>
            <Tag>{{ resourceTotal }}</Tag>
          </div>
          <div
            v-if="isAdmin"
            class="management-toolbar__actions management-toolbar__group"
          >
            <Button
              :loading="exportSubmitting"
              size="small"
              @click="exportResources"
            >
              <template #icon>
                <Download class="size-4" />
              </template>
              导出
            </Button>
            <Button size="small" type="primary" @click="openCreateModal">
              <template #icon>
                <Plus class="size-4" />
              </template>
              新增
            </Button>
            <Button size="small" @click="openImportModal">
              <template #icon>
                <Inbox class="size-4" />
              </template>
              导入
            </Button>
          </div>
        </div>
        <Table
          :columns="columns"
          :data-source="resources"
          :loading="loading"
          :pagination="tablePagination(resourcePage, resourceTotal)"
          :scroll="{ x: 1940 }"
          row-key="id"
          size="small"
          @change="changePage"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'management_status'">
              <Tag :color="statusColor(record.management_status)">
                {{ record.management_status }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'occupancy_status'">
              <Tag :color="statusColor(record.occupancy_status)">
                {{ record.occupancy_status }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'test_status'">
              <Space :size="4">
                <Tag :color="statusColor(record.test_status)">
                  {{ resourceTestStatusLabel(record.test_status) }}
                </Tag>
                <Button
                  v-if="record.current_test_job_id"
                  size="small"
                  type="link"
                  @click="
                    router.push(`/test-jobs/${record.current_test_job_id}`)
                  "
                >
                  查看测试
                </Button>
              </Space>
            </template>
            <template v-else-if="column.dataIndex === 'current_lease_username'">
              {{ displayValue(record.current_lease_username) }}
            </template>
            <template
              v-else-if="column.dataIndex === 'current_lease_expected_ends_at'"
            >
              {{ formatTime(record.current_lease_expected_ends_at) }}
            </template>
            <template v-else-if="column.dataIndex === 'tags'">
              <Space v-if="record.tags.length > 0" :size="[4, 4]" wrap>
                <Tag v-for="tag in record.tags" :key="tag">{{ tag }}</Tag>
              </Space>
              <template v-else>-</template>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space wrap>
                <Button
                  size="small"
                  type="link"
                  @click="openTableDetail(record)"
                >
                  <template #icon>
                    <Eye class="size-4" />
                  </template>
                  详情
                </Button>
                <Button
                  v-if="canEdit(asResourceRecord(record))"
                  :disabled="
                    !canUseResourceDestructiveActions(asResourceRecord(record))
                  "
                  size="small"
                  type="link"
                  @click="openEditModal(asResourceRecord(record))"
                >
                  <template #icon>
                    <UserRoundPen class="size-4" />
                  </template>
                  编辑
                </Button>
                <Button
                  v-if="canInstall(asResourceRecord(record))"
                  :disabled="
                    !canUseResourceDestructiveActions(asResourceRecord(record))
                  "
                  danger
                  size="small"
                  type="link"
                  :loading="installing"
                  @click="openInstallModal(asResourceRecord(record))"
                >
                  <template #icon>
                    <RotateCw class="size-4" />
                  </template>
                  重装
                </Button>
                <Button
                  v-if="canOccupy(asResourceRecord(record))"
                  size="small"
                  type="link"
                  @click="openLeaseModal(asResourceRecord(record))"
                >
                  <template #icon>
                    <Plus class="size-4" />
                  </template>
                  占用
                </Button>
                <Button
                  v-if="canRelease(asResourceRecord(record))"
                  :disabled="
                    !canUseResourceDestructiveActions(asResourceRecord(record))
                  "
                  size="small"
                  type="link"
                  @click="releaseResource(asResourceRecord(record))"
                >
                  <template #icon>
                    <LogOut class="size-4" />
                  </template>
                  释放
                </Button>
                <Button
                  v-if="canRenew(asResourceRecord(record))"
                  size="small"
                  type="link"
                  @click="openRenewModal(asResourceRecord(record))"
                >
                  <template #icon>
                    <RotateCw class="size-4" />
                  </template>
                  续期
                </Button>
                <Button
                  v-if="canForceRelease(asResourceRecord(record))"
                  :disabled="
                    !canUseResourceDestructiveActions(asResourceRecord(record))
                  "
                  danger
                  size="small"
                  type="link"
                  @click="releaseResource(asResourceRecord(record), true)"
                >
                  <template #icon>
                    <LogOut class="size-4" />
                  </template>
                  强制释放
                </Button>
              </Space>
            </template>
            <template v-else>
              {{ displayValue(text) }}
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <Drawer
      v-model:open="detailOpen"
      :destroy-on-close="true"
      :width="720"
      placement="right"
      title="资源详情"
    >
      <template #extra v-if="selectedResource">
        <Space wrap>
          <Button
            v-if="canEdit(selectedResource)"
            :disabled="!canUseResourceDestructiveActions(selectedResource)"
            size="small"
            @click="openEditModal(selectedResource)"
          >
            <template #icon>
              <UserRoundPen class="size-4" />
            </template>
            编辑
          </Button>
          <Button
            v-if="canProbe(selectedResource)"
            size="small"
            type="link"
            :loading="probing"
            @click="probeHardware(selectedResource)"
          >
            <template #icon>
              <RotateCw class="size-4" />
            </template>
            刷新硬件
          </Button>
          <Button
            v-if="canOccupy(selectedResource)"
            size="small"
            type="primary"
            @click="openLeaseModal(selectedResource)"
          >
            <template #icon>
              <Plus class="size-4" />
            </template>
            占用
          </Button>
          <Button
            v-if="canRelease(selectedResource)"
            :disabled="!canUseResourceDestructiveActions(selectedResource)"
            size="small"
            @click="releaseResource(selectedResource)"
          >
            <template #icon>
              <LogOut class="size-4" />
            </template>
            释放
          </Button>
          <Button
            v-if="canForceRelease(selectedResource)"
            :disabled="!canUseResourceDestructiveActions(selectedResource)"
            danger
            size="small"
            @click="releaseResource(selectedResource, true)"
          >
            <template #icon>
              <LogOut class="size-4" />
            </template>
            强制释放
          </Button>
        </Space>
      </template>
      <template v-if="selectedResource">
        <Descriptions bordered :column="1" size="small">
          <DescriptionsItem label="资源编码">
            {{ selectedResource.resource_code }}
          </DescriptionsItem>
          <DescriptionsItem label="显示名">
            {{ selectedResource.name }}
          </DescriptionsItem>
          <DescriptionsItem label="资源类型">
            {{ selectedResource.resource_type }}
          </DescriptionsItem>
          <DescriptionsItem label="管理状态">
            <Tag :color="statusColor(selectedResource.management_status)">
              {{ selectedResource.management_status }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="测试状态">
            <Space :size="4">
              <Tag :color="statusColor(selectedResource.test_status)">
                {{ resourceTestStatusLabel(selectedResource.test_status) }}
              </Tag>
              <Button
                v-if="selectedResource.current_test_job_id"
                size="small"
                type="link"
                @click="
                  router.push(
                    `/test-jobs/${selectedResource.current_test_job_id}`,
                  )
                "
              >
                查看测试
              </Button>
            </Space>
          </DescriptionsItem>
          <DescriptionsItem label="连通状态">
            <Tag :color="statusColor(selectedResource.connectivity_status)">
              {{ selectedResource.connectivity_status }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="关键资源">
            {{ selectedResource.is_critical ? '是' : '否' }}
          </DescriptionsItem>
          <DescriptionsItem label="OS IP">
            {{ selectedResource.primary_ip }}
          </DescriptionsItem>
          <DescriptionsItem label="SSH 账号">
            {{ selectedResource.ssh_username }}
          </DescriptionsItem>
          <DescriptionsItem label="SSH 密码">
            {{
              credentialValue(
                selectedResource.has_ssh_password,
                credentials?.ssh_password,
              )
            }}
          </DescriptionsItem>
          <DescriptionsItem label="MAC">
            {{ displayValue(selectedResource.mac_address) }}
          </DescriptionsItem>
          <DescriptionsItem label="BMC IP">
            {{ displayValue(selectedResource.bmc_ip) }}
          </DescriptionsItem>
          <DescriptionsItem label="BMC 账号">
            {{ displayValue(selectedResource.bmc_username) }}
          </DescriptionsItem>
          <DescriptionsItem label="BMC 密码">
            {{
              credentialValue(
                selectedResource.has_bmc_password,
                credentials?.bmc_password,
              )
            }}
          </DescriptionsItem>
          <DescriptionsItem label="设备位置">
            {{ displayValue(selectedResource.device_location) }}
          </DescriptionsItem>
          <DescriptionsItem label="设备分布">
            {{ displayValue(selectedResource.device_distribution) }}
          </DescriptionsItem>
          <DescriptionsItem label="架构">
            {{ displayValue(selectedResource.arch) }}
          </DescriptionsItem>
          <DescriptionsItem label="OS">
            {{ displayValue(selectedResource.os_version) }}
          </DescriptionsItem>
          <DescriptionsItem label="内核">
            {{ displayValue(selectedResource.kernel_version) }}
          </DescriptionsItem>
          <DescriptionsItem label="CPU">
            {{ displayValue(selectedResource.cpu_model) }}
          </DescriptionsItem>
          <DescriptionsItem label="CPU 数量">
            {{ displayValue(selectedResource.cpu_count) }}
          </DescriptionsItem>
          <DescriptionsItem label="内存数量">
            {{ displayValue(selectedResource.memory_count) }}
          </DescriptionsItem>
          <DescriptionsItem label="内存">
            {{ displayValue(selectedResource.memory_spec) }}
          </DescriptionsItem>
          <DescriptionsItem label="HDD 数量">
            {{ displayValue(selectedResource.hdd_count) }}
          </DescriptionsItem>
          <DescriptionsItem label="HDD">
            {{ displayValue(selectedResource.hdd_spec) }}
          </DescriptionsItem>
          <DescriptionsItem label="SSD 盘数量">
            {{ displayValue(selectedResource.ssd_count) }}
          </DescriptionsItem>
          <DescriptionsItem label="SSD">
            {{ displayValue(selectedResource.ssd_spec) }}
          </DescriptionsItem>
          <DescriptionsItem label="SSD 卡数量">
            {{ displayValue(selectedResource.ssd_card_count) }}
          </DescriptionsItem>
          <DescriptionsItem label="SSD 卡规格">
            {{ displayValue(selectedResource.ssd_card_spec) }}
          </DescriptionsItem>
          <DescriptionsItem label="主板 SN">
            {{ displayValue(selectedResource.board_sn) }}
          </DescriptionsItem>
          <DescriptionsItem label="占用状态">
            <Tag :color="statusColor(selectedResource.occupancy_status)">
              {{ selectedResource.occupancy_status }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="占用人">
            {{ displayValue(selectedResource.current_lease_username) }}
          </DescriptionsItem>
          <DescriptionsItem label="占用用途">
            {{ displayValue(selectedResource.current_lease_purpose) }}
          </DescriptionsItem>
          <DescriptionsItem label="占用到">
            {{ formatTime(selectedResource.current_lease_expected_ends_at) }}
          </DescriptionsItem>
          <DescriptionsItem label="使用场景">
            {{ displayValue(selectedResource.usage_scenario) }}
          </DescriptionsItem>
          <DescriptionsItem label="标签">
            <Space v-if="selectedResource.tags.length > 0" :size="[4, 4]" wrap>
              <Tag v-for="tag in selectedResource.tags" :key="tag">
                {{ tag }}
              </Tag>
            </Space>
            <template v-else>-</template>
          </DescriptionsItem>
          <DescriptionsItem label="扩展 JSON">
            <pre class="management-json">{{
              JSON.stringify(selectedResource.extra ?? {}, null, 2)
            }}</pre>
          </DescriptionsItem>
        </Descriptions>
      </template>
    </Drawer>

    <Modal
      v-model:open="editOpen"
      :confirm-loading="editSubmitting"
      destroy-on-close
      :title="isCreatingResource ? '新增物理机' : '编辑物理机'"
      width="760px"
      @ok="submitEditResource"
    >
      <Form ref="editFormRef" :model="editForm" layout="vertical" class="pt-2">
        <div class="management-edit-grid">
          <FormItem
            v-if="isCreatingResource"
            label="设备整机 SN"
            name="resource_code"
            :rules="[{ required: true, message: '请输入设备整机 SN' }]"
          >
            <Input v-model:value="editForm.resource_code" />
          </FormItem>
          <FormItem
            label="管理状态"
            name="management_status"
            :rules="[{ required: true, message: '请选择管理状态' }]"
          >
            <Select
              v-model:value="editForm.management_status"
              :options="managementStatusOptions"
            />
          </FormItem>
          <FormItem
            label="连通状态"
            name="connectivity_status"
            :rules="[{ required: true, message: '请选择连通状态' }]"
          >
            <Select
              v-model:value="editForm.connectivity_status"
              :options="connectivityStatusOptions"
            />
          </FormItem>
          <FormItem label="关键资源" name="is_critical">
            <AntSwitch
              v-model:checked="editForm.is_critical"
              checked-children="是"
              un-checked-children="否"
            />
          </FormItem>
          <FormItem label="标签" name="tags">
            <Input v-model:value="editForm.tags" placeholder="vm-host, ci" />
          </FormItem>
          <FormItem label="显示名" name="name">
            <Input v-model:value="editForm.name" />
          </FormItem>
          <FormItem
            label="OS IP"
            name="primary_ip"
            :rules="[{ required: true, message: '请输入 OS IP' }]"
          >
            <Input v-model:value="editForm.primary_ip" />
          </FormItem>
          <FormItem label="MAC" name="mac_address">
            <Input v-model:value="editForm.mac_address" />
          </FormItem>
          <FormItem
            label="SSH 账号"
            name="ssh_username"
            :rules="[{ required: true, message: '请输入 SSH 账号' }]"
          >
            <Input v-model:value="editForm.ssh_username" />
          </FormItem>
          <FormItem
            :label="isCreatingResource ? 'SSH 密码' : 'SSH 新密码'"
            name="ssh_password"
            :rules="
              isCreatingResource
                ? [{ required: true, message: '请输入 SSH 密码' }]
                : []
            "
          >
            <Input
              v-model:value="editForm.ssh_password"
              :placeholder="isCreatingResource ? undefined : '留空不修改'"
              type="password"
            />
          </FormItem>
          <FormItem
            label="BMC IP"
            name="bmc_ip"
            :rules="[{ required: true, message: '请输入 BMC IP' }]"
          >
            <Input v-model:value="editForm.bmc_ip" />
          </FormItem>
          <FormItem
            label="BMC 账号"
            name="bmc_username"
            :rules="[{ required: true, message: '请输入 BMC 账号' }]"
          >
            <Input v-model:value="editForm.bmc_username" />
          </FormItem>
          <FormItem
            :label="isCreatingResource ? 'BMC 密码' : 'BMC 新密码'"
            name="bmc_password"
            :rules="
              isCreatingResource
                ? [{ required: true, message: '请输入 BMC 密码' }]
                : []
            "
          >
            <Input
              v-model:value="editForm.bmc_password"
              :placeholder="isCreatingResource ? undefined : '留空不修改'"
              type="password"
            />
          </FormItem>
          <FormItem label="设备位置" name="device_location">
            <Input v-model:value="editForm.device_location" />
          </FormItem>
          <FormItem label="设备分布" name="device_distribution">
            <Input v-model:value="editForm.device_distribution" />
          </FormItem>
          <FormItem label="架构" name="arch">
            <Input v-model:value="editForm.arch" />
          </FormItem>
          <FormItem label="OS" name="os_version">
            <Input v-model:value="editForm.os_version" />
          </FormItem>
          <FormItem label="内核" name="kernel_version">
            <Input v-model:value="editForm.kernel_version" />
          </FormItem>
          <FormItem label="CPU" name="cpu_model">
            <Input v-model:value="editForm.cpu_model" />
          </FormItem>
          <FormItem label="CPU 数量" name="cpu_count">
            <InputNumber
              v-model:value="editForm.cpu_count"
              :min="0"
              class="w-full"
            />
          </FormItem>
          <FormItem label="内存数量" name="memory_count">
            <InputNumber
              v-model:value="editForm.memory_count"
              :min="0"
              class="w-full"
            />
          </FormItem>
          <FormItem label="内存规格" name="memory_spec">
            <Input v-model:value="editForm.memory_spec" />
          </FormItem>
          <FormItem label="HDD 数量" name="hdd_count">
            <InputNumber
              v-model:value="editForm.hdd_count"
              :min="0"
              class="w-full"
            />
          </FormItem>
          <FormItem label="HDD 规格" name="hdd_spec">
            <Input v-model:value="editForm.hdd_spec" />
          </FormItem>
          <FormItem label="SSD 盘数量" name="ssd_count">
            <InputNumber
              v-model:value="editForm.ssd_count"
              :min="0"
              class="w-full"
            />
          </FormItem>
          <FormItem label="SSD 盘规格" name="ssd_spec">
            <Input v-model:value="editForm.ssd_spec" />
          </FormItem>
          <FormItem label="SSD 卡数量" name="ssd_card_count">
            <InputNumber
              v-model:value="editForm.ssd_card_count"
              :min="0"
              class="w-full"
            />
          </FormItem>
          <FormItem label="SSD 卡规格" name="ssd_card_spec">
            <Input v-model:value="editForm.ssd_card_spec" />
          </FormItem>
          <FormItem label="主板 SN" name="board_sn">
            <Input v-model:value="editForm.board_sn" />
          </FormItem>
          <FormItem
            class="management-edit-grid__full"
            label="使用场景"
            name="usage_scenario"
          >
            <Input v-model:value="editForm.usage_scenario" />
          </FormItem>
          <FormItem
            class="management-edit-grid__full"
            label="扩展 JSON"
            name="extra"
          >
            <Input v-model:value="editForm.extra" />
          </FormItem>
        </div>
      </Form>
    </Modal>

    <Modal
      v-model:open="leaseOpen"
      :confirm-loading="leaseSubmitting"
      destroy-on-close
      title="占用资源"
      @ok="submitLease"
    >
      <div class="space-y-4" v-if="leaseTarget">
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="资源">
            {{ leaseTarget.primary_ip }}
            <template v-if="leaseTarget.name">
              / {{ leaseTarget.name }}
            </template>
          </DescriptionsItem>
        </Descriptions>
        <div>
          <span class="management-filter__label">占用用途</span>
          <Input
            v-model:value="leaseForm.purpose"
            placeholder="例如：调试 openEuler"
          />
        </div>
        <div>
          <Checkbox v-if="isAdmin" v-model:checked="leaseForm.permanent">
            永久占用
          </Checkbox>
          <DatePicker
            v-if="!isAdmin || !leaseForm.permanent"
            v-model:value="leaseForm.expectedEndsAt"
            :disabled-date="disabledLeaseDate"
            class="mt-2 w-full"
            format="YYYY-MM-DD HH:mm"
            show-time
          />
        </div>
      </div>
    </Modal>

    <Modal
      v-model:open="renewOpen"
      :confirm-loading="renewSubmitting"
      destroy-on-close
      title="续期租约"
      @ok="submitRenew"
    >
      <div class="space-y-4" v-if="renewTarget">
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="资源">
            {{ renewTarget.primary_ip }}
            <template v-if="renewTarget.name">
              / {{ renewTarget.name }}
            </template>
          </DescriptionsItem>
          <DescriptionsItem label="当前到期">
            {{ formatTime(renewTarget.current_lease_expected_ends_at) }}
          </DescriptionsItem>
        </Descriptions>
        <div>
          <span class="management-filter__label">续期到</span>
          <DatePicker
            v-model:value="renewForm.expectedEndsAt"
            :disabled-date="disabledRenewDate"
            class="mt-2 w-full"
            format="YYYY-MM-DD HH:mm"
            show-time
          />
        </div>
      </div>
    </Modal>

    <Modal
      v-model:open="importOpen"
      :destroy-on-close="true"
      title="导入资源"
      width="760px"
    >
      <div class="space-y-4">
        <RadioGroup
          v-model:value="importTarget"
          button-style="solid"
          size="small"
        >
          <RadioButton value="resources">资源</RadioButton>
          <RadioButton value="leases">租约</RadioButton>
        </RadioGroup>

        <Upload
          :before-upload="beforeImportFile"
          :file-list="importFileList"
          :max-count="1"
          accept=".csv,text/csv"
          @remove="removeImportFile"
        >
          <Button>
            <template #icon>
              <Inbox class="size-4" />
            </template>
            选择 CSV
          </Button>
        </Upload>

        <Descriptions v-if="importResult" bordered :column="3" size="small">
          <DescriptionsItem label="总行数">
            {{ importResult.total_rows }}
          </DescriptionsItem>
          <DescriptionsItem label="成功">
            {{ importResult.success_count }}
          </DescriptionsItem>
          <DescriptionsItem label="失败">
            {{ importResult.error_count }}
          </DescriptionsItem>
        </Descriptions>

        <Table
          v-if="importResult"
          :columns="importResultColumns"
          :data-source="importResult.rows"
          :pagination="false"
          :scroll="{ x: 720, y: 260 }"
          row-key="row_number"
          size="small"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'status'">
              <Tag :color="importStatusColor(record.status)">
                {{ record.status }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'errors'">
              {{ record.errors.join('; ') }}
            </template>
            <template v-else>
              {{ displayValue(text) }}
            </template>
          </template>
        </Table>
      </div>
      <template #footer>
        <Button @click="importOpen = false">关闭</Button>
        <Button
          :disabled="!importFile"
          :loading="importPreviewing"
          @click="previewCsvImport"
        >
          校验
        </Button>
        <Button
          :disabled="!importFile"
          :loading="importSubmitting"
          type="primary"
          @click="submitCsvImport"
        >
          导入
        </Button>
      </template>
    </Modal>
    <Modal
      v-model:open="installModalVisible"
      title="重装系统"
      :confirm-loading="installing"
      ok-text="开始装机"
      cancel-text="取消"
      ok-type="danger"
      @ok="handleInstall"
    >
      <div style="margin-bottom: 12px">
        将通过 PXE
        重装物理机系统。安装期间资源状态变为「维护中」，完成后自动恢复。root
        密码将重置为默认密码。此操作不可逆。
      </div>
      <div style="margin-bottom: 4px; font-size: 13px; color: #666">版本</div>
      <Select
        v-model:value="installSelectedOsVersion"
        :options="installOsVersionGroups"
        placeholder="选择版本"
        style="width: 100%; margin-bottom: 8px"
        @change="
          () => {
            installSelectedRound = '';
            installSelectedKernel = '';
          }
        "
      />
      <div style="margin-bottom: 4px; font-size: 13px; color: #666">轮次</div>
      <Select
        v-model:value="installSelectedRound"
        :options="installRoundOptions"
        :disabled="!installSelectedOsVersion"
        placeholder="选择轮次"
        style="width: 100%; margin-bottom: 8px"
        @change="() => (installSelectedKernel = '')"
      />
      <div style="margin-bottom: 4px; font-size: 13px; color: #666">内核</div>
      <Select
        v-model:value="installSelectedKernel"
        :options="installKernelOptions"
        :disabled="!installSelectedRound"
        placeholder="选择内核"
        style="width: 100%"
      />
      <template v-if="isAdmin && Object.keys(installBaseVariants).length > 0">
        <Divider style="margin: 12px 0 8px; font-size: 12px">
          基础内核配置（缺本地树的变体以此为基础装完后换内核）
        </Divider>
        <div
          v-for="os in Object.keys(installBaseVariants).sort()"
          :key="os"
          style="
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 6px;
          "
        >
          <span
            style="
              flex: 1;
              overflow: hidden;
              text-overflow: ellipsis;
              font-size: 12px;
              white-space: nowrap;
            "
            :title="os"
          >
            {{ os }}
          </span>
          <Input
            v-model:value="installBaseDrafts[os]"
            size="small"
            style="width: 120px"
            placeholder="如 6.6"
          />
          <Button
            size="small"
            :loading="installBaseSaving"
            @click="saveInstallBaseVariant(os)"
          >
            保存
          </Button>
        </div>
      </template>
    </Modal>
  </Page>
</template>
