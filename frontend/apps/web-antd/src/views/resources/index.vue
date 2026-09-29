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
