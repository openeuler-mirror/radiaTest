<script lang="ts" setup>
import type {
  TableColumnsType,
  TablePaginationConfig,
  UploadProps,
} from 'ant-design-vue';
import type { Dayjs } from 'dayjs';

import type { VMInstallType, VMRequestField } from './vm-request-form';

import type {
  ResourceCredentialRecord,
  ResourceRecord,
  TaskEventRecord,
  UserRole,
  VMImageRecord,
  VMPowerAction,
  VMRequestRecord,
} from '#/api';

import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ExternalLink, Eye, Inbox, LogOut, Plus, RotateCw } from '@vben/icons';
import { useUserStore } from '@vben/stores';

import {
  Button,
  Card,
  Checkbox,
  CheckboxGroup,
  DatePicker,
  Descriptions,
  DescriptionsItem,
  Drawer,
  Input,
  InputNumber,
  message,
  Modal,
  Progress,
  Select,
  Space,
  Table,
  TabPane,
  Tabs,
  Tag,
  Upload,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  batchReleaseVMApi,
  cancelVMRequestApi,
  createVMBatchApi,
  createVMRequestApi,
  extendLeaseApi,
  getKernelVariantsApi,
  getResourceApi,
  getResourceCredentialsApi,
  getVMImagesApi,
  getVMPowerApi,
  getVMRequestEventsApi,
  getVMRequestsApi,
  getVMsApi,
  operateVMPowerApi,
  refreshVMIpApi,
  releaseVMApi,
  updateResourceApi,
  uploadVMISOApi,
} from '#/api';

import {
  createIdempotencyAttempt,
  idempotencyKeyFor,
  resetIdempotencyAttempt,
} from '../_shared/idempotency';
import { createLatestRequestGuard } from '../_shared/latest-request';
import { tablePagination } from '../_shared/table-pagination';
import { resolveVMISOUrl, validateVMISOFile } from './vm-iso-upload';
import {
  buildVMRequestPayload,
  isVMRequestFieldRequired,
  validateVMRequestForm,
} from './vm-request-form';
import {
  canEditVMCredentials as canEditVMCredentialsForContext,
  canOpenVMConsole,
  canRefreshVMIp as canRefreshVMIpForContext,
  canReleaseVM,
  canRenewVM,
  canViewVMCredentials,
  displayCredentialValue,
  displayValue,
  eventLevelColor,
  eventPhaseLabel,
  formatDataDisks,
  formatRequestImage,
  formatRequestSpec,
  formatSpec,
  formatTaskEventMessage,
  installTypeLabel,
  isHostCommandEvent,
  powerActionLabel,
  powerStateColor,
  powerStateLabel,
  shouldDisplayTaskEvent,
  statusColor,
  statusLabel,
  uniqueOptions,
  vmConsoleTabTitle,
} from './vm-view';

type ActiveTab = 'requests' | 'vms';

const activeTab = ref<ActiveTab>('vms');
const showAll = ref(false);
const loading = ref(false);
const requestOpen = ref(false);
const requestSubmitting = ref(false);
const isoUploading = ref(false);
const isoUploadProgress = ref(0);
const isoUploadController = ref<AbortController>();
const renewOpen = ref(false);
const renewSubmitting = ref(false);
const credentialLoading = ref(false);
const refreshingIpId = ref<null | string>(null);
const detailOpen = ref(false);
const requestDetailOpen = ref(false);
const requestEventsLoading = ref(false);
const powerLoading = ref(false);
const powerActionLoading = ref<null | VMPowerAction>(null);
const passwordOpen = ref(false);
const passwordSubmitting = ref(false);
const selectedVmIds = ref<string[]>([]);
const images = ref<VMImageRecord[]>([]);
const vms = ref<ResourceRecord[]>([]);
const requests = ref<VMRequestRecord[]>([]);
const vmPage = ref(1);
const vmTotal = ref(0);
const searchQuery = ref('');
let searchTimer: null | ReturnType<typeof setTimeout> = null;
const requestPage = ref(1);
const requestTotal = ref(0);
const requestEvents = ref<TaskEventRecord[]>([]);
const powerState = ref<null | string>(null);
const powerStateError = ref('');
const selectedVM = ref<null | ResourceRecord>(null);
const selectedRequest = ref<null | VMRequestRecord>(null);
const renewTarget = ref<null | ResourceRecord>(null);
const credentials = ref<null | ResourceCredentialRecord>(null);
let credentialRequestToken = 0;
const vmListRequest = createLatestRequestGuard();
const powerStateRequest = createLatestRequestGuard();
const requestEventsRequest = createLatestRequestGuard();
const requestIdempotency = createIdempotencyAttempt();
const renewIdempotency = createIdempotencyAttempt();
const powerIdempotency = createIdempotencyAttempt();
const userStore = useUserStore();
const router = useRouter();
const route = useRoute();

const requestForm = reactive({
  archSelections: ['aarch64'] as string[],
  aarch64Count: 1,
  x86_64Count: 1,
  dataDiskCount: 0,
  dist: 'openEuler',
  expectedEndsAt: dayjs().add(1, 'day') as Dayjs | undefined,
  extraNicNum: 0,
  imageRound: '',
  imageUrl: '',
  kernelVariant: '',
  kernelRpmUrl: '',
  installType: 'auto' as VMInstallType,
  memoryMb: 4096,
  osVersion: '',
  permanent: false,
  purpose: '',
  vcpuCount: 2,
});
const renewForm = reactive({
  expectedEndsAt: dayjs().add(1, 'day') as Dayjs | undefined,
});
const passwordForm = reactive({
  sshPassword: '',
});

const vmColumns: TableColumnsType<ResourceRecord> = [
  {
    dataIndex: 'vm_name',
    ellipsis: true,
    fixed: 'left',
    title: 'VM 名称',
    width: 280,
  },
  { dataIndex: 'primary_ip', title: 'OS IP', width: 150 },
  { key: 'vnc', title: 'VNC', width: 180 },
  { dataIndex: 'arch', title: '架构', width: 100 },
  { dataIndex: 'os_version', title: 'OS', width: 190 },
  { key: 'spec', title: '规格', width: 180 },
  { dataIndex: 'current_lease_username', title: '占用人', width: 120 },
  { dataIndex: 'current_lease_expected_ends_at', title: '占用到', width: 180 },
  { fixed: 'right', key: 'action', title: '', width: 250 },
];

const requestColumns: TableColumnsType<VMRequestRecord> = [
  { dataIndex: 'status', fixed: 'left', title: '状态', width: 110 },
  { dataIndex: 'install_type', title: '安装方式', width: 110 },
  { dataIndex: 'os_version', title: 'OS', width: 190 },
  { dataIndex: 'image_round', title: '轮次', width: 110 },
  { dataIndex: 'arch', title: '架构', width: 100 },
  { dataIndex: 'image_url', ellipsis: true, title: '镜像 URL', width: 260 },
  { key: 'spec', title: '规格', width: 190 },
  { dataIndex: 'requester_username', title: '申请人', width: 120 },
  { dataIndex: 'purpose', ellipsis: true, title: '用途', width: 180 },
  { dataIndex: 'created_at', title: '创建时间', width: 180 },
  { dataIndex: 'error_message', ellipsis: true, title: '错误', width: 220 },
  { fixed: 'right', key: 'action', title: '', width: 170 },
];

const currentUserId = computed(() => userStore.userInfo?.userId);
const currentRole = computed(
  () => userStore.userInfo?.roles?.[0] as undefined | UserRole,
);
const isAdmin = computed(() => currentRole.value === 'ADMIN');
const visibleRequestEvents = computed(() =>
  requestEvents.value.filter((event) =>
    shouldDisplayTaskEvent(event.phase, event.message),
  ),
);
const vmAuthContext = computed(() => ({
  currentRole: currentRole.value,
  currentUserId: currentUserId.value,
}));
const installTypeOptions = [
  { label: '自动', value: 'auto' },
  { label: '手动', value: 'manual' },
];

const distOptions = computed(() =>
  uniqueOptions(images.value.map((image) => image.dist)),
);
// 2403sp4-64k 是 2403sp4 的 64k 变体（无独立 qcow2 镜像，后处理装 kernel-64k），
// 仅当 2403sp4 base 镜像存在时作为可选项出现。
const KERNEL_64K_OS_VERSION = 'openEuler-24.03-LTS-SP4-64k';
const KERNEL_64K_BASE = 'openEuler-24.03-LTS-SP4';
const osVersionOptions = computed(() => {
  const base = uniqueOptions(
    images.value
      .filter((image) => image.dist === requestForm.dist)
      .map((image) => image.os_version),
  );
  if (base.some((option) => option.value === KERNEL_64K_BASE)) {
    base.push({ label: KERNEL_64K_OS_VERSION, value: KERNEL_64K_OS_VERSION });
  }
  return base;
});
const roundOptions = computed(() =>
  // -64k 选项无独立镜像，按 base 版（去掉 -64k 后缀）取 round。
  uniqueOptions(
    images.value
      .filter(
        (image) =>
          image.dist === requestForm.dist &&
          image.os_version === requestForm.osVersion.replace(/-64k$/, ''),
      )
      .map((image) => image.image_round),
  ),
);

const kernelVariantOptions = ref<{ label: string; value: string }[]>([]);
const kernelVariantsLoading = ref(false);

async function loadKernelVariants() {
  const arch = requestForm.archSelections[0];
  if (!requestForm.osVersion || !requestForm.imageRound || !arch) {
    kernelVariantOptions.value = [];
    return;
  }
  kernelVariantsLoading.value = true;
  try {
    const variants = await getKernelVariantsApi({
      arch,
      image_round: requestForm.imageRound,
      os_version: requestForm.osVersion,
    });
    kernelVariantOptions.value = variants.map((v) => ({
      label: `${v.kernel_version_prefix} (${v.variant})`,
      value: v.variant,
    }));
  } catch {
    kernelVariantOptions.value = [];
  } finally {
    kernelVariantsLoading.value = false;
  }
}

function onKernelVariantChange() {
  if (requestForm.kernelVariant) requestForm.kernelRpmUrl = '';
}

function onKernelRpmUrlInput() {
  if (requestForm.kernelRpmUrl) requestForm.kernelVariant = '';
}
function createIdempotencyKey(action: string) {
  return `${action}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function credentialValue(hasPassword: boolean, value?: null | string) {
  return displayCredentialValue(
    hasPassword,
    Boolean(selectedVM.value && canViewCredentials(selectedVM.value)),
    credentialLoading.value,
    value,
  );
}

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function asResourceRecord(record: Record<string, unknown>) {
  return record as unknown as ResourceRecord;
}

function asVMRequestRecord(record: Record<string, unknown>) {
  return record as unknown as VMRequestRecord;
}

function formatAttemptTitle(attempt: Record<string, unknown>, index: number) {
  const hostIp = displayValue(attempt.host_ip);
  const attemptNo = displayValue(attempt.attempt);
  return `#${index + 1} 宿主 ${hostIp} / 第 ${attemptNo} 次`;
}

function formatAttemptValue(attempt: Record<string, unknown>, key: string) {
  return displayValue(attempt[key]);
}

function formatAttemptStatus(attempt: Record<string, unknown>) {
  return String(attempt.status ?? '');
}

function requiredLabelClass(field: VMRequestField) {
  return {
    'management-filter__label--required': isVMRequestFieldRequired(
      field,
      requestForm,
      isAdmin.value,
    ),
  };
}

function canRelease(record: ResourceRecord) {
  return canReleaseVM(record, vmAuthContext.value);
}

function canRenew(record: ResourceRecord) {
  return canRenewVM(record, vmAuthContext.value);
}

function canViewCredentials(record: ResourceRecord) {
  return canViewVMCredentials(record, vmAuthContext.value);
}

function canOpenConsole(record: ResourceRecord) {
  return canOpenVMConsole(record, vmAuthContext.value);
}

function canRefreshVMIp(record: ResourceRecord) {
  return canRefreshVMIpForContext(record, vmAuthContext.value);
}

function canEditVMCredentials(record: ResourceRecord) {
  return canEditVMCredentialsForContext(record, vmAuthContext.value);
}

function updateVMRecord(record: ResourceRecord) {
  vms.value = vms.value.map((item) => (item.id === record.id ? record : item));
  if (selectedVM.value?.id === record.id) {
    selectedVM.value = record;
  }
}

function syncSelection() {
  if (requestForm.installType === 'manual') return;
  if (!requestForm.dist && distOptions.value[0]) {
    requestForm.dist = String(distOptions.value[0].value);
  }
  if (
    requestForm.osVersion &&
    osVersionOptions.value.some((item) => item.value === requestForm.osVersion)
  ) {
    return;
  }
  requestForm.osVersion = String(osVersionOptions.value[0]?.value ?? '');
}

function syncRound() {
  if (requestForm.installType === 'manual') return;
  if (
    requestForm.imageRound &&
    roundOptions.value.some((item) => item.value === requestForm.imageRound)
  ) {
    return;
  }
  requestForm.imageRound = String(roundOptions.value[0]?.value ?? '');
}

async function loadImages() {
  images.value = await getVMImagesApi();
  syncSelection();
  syncRound();
}

async function loadData() {
  const request = vmListRequest.begin();
  loading.value = true;
  try {
    const [vmRows, requestRows] = await Promise.all([
      getVMsApi(showAll.value, vmPage.value, searchQuery.value || undefined),
      getVMRequestsApi(showAll.value, requestPage.value),
    ]);
    request.commit(() => {
      vms.value = vmRows.items;
      vmTotal.value = vmRows.total;
      requests.value = requestRows.items;
      requestTotal.value = requestRows.total;
      if (selectedRequest.value) {
        selectedRequest.value =
          requestRows.items.find(
            (row) => row.id === selectedRequest.value?.id,
          ) ?? selectedRequest.value;
      }
    });
  } finally {
    request.commit(() => {
      loading.value = false;
    });
  }
}

async function loadRequestEvents(requestId = selectedRequest.value?.id) {
  if (!requestId) return;
  const request = requestEventsRequest.begin();
  requestEventsLoading.value = true;
  try {
    const events = await getVMRequestEventsApi(requestId);
    request.commit(() => {
      if (requestDetailOpen.value && selectedRequest.value?.id === requestId) {
        requestEvents.value = events;
      }
    });
  } finally {
    request.commit(() => {
      requestEventsLoading.value = false;
    });
  }
}

async function loadPowerState(record = selectedVM.value) {
  const request = powerStateRequest.begin();
  powerState.value = null;
  powerStateError.value = '';
  if (!record || !canOpenConsole(record)) {
    powerLoading.value = false;
    return;
  }

  powerLoading.value = true;
  try {
    const result = await getVMPowerApi(record.id);
    request.commit(() => {
      if (detailOpen.value && selectedVM.value?.id === record.id) {
        powerState.value = result.power_state;
      }
    });
  } catch {
    request.commit(() => {
      if (detailOpen.value && selectedVM.value?.id === record.id) {
        powerStateError.value = '获取失败';
      }
    });
  } finally {
    request.commit(() => {
      powerLoading.value = false;
    });
  }
}

function openRequestModal() {
  requestForm.archSelections = ['aarch64'];
  requestForm.aarch64Count = 1;
  requestForm.x86_64Count = 1;
  requestForm.dataDiskCount = 0;
  requestForm.dist = '';
  requestForm.expectedEndsAt = isAdmin.value
    ? dayjs().add(7, 'day')
    : dayjs().add(1, 'day');
  requestForm.extraNicNum = 0;
  requestForm.imageRound = '';
  requestForm.imageUrl = '';
  requestForm.kernelVariant = '';
  requestForm.kernelRpmUrl = '';
  requestForm.installType = 'auto';
  requestForm.memoryMb = 4096;
  requestForm.osVersion = '';
  requestForm.permanent = false;
  requestForm.purpose = '';
  requestForm.vcpuCount = 2;
  isoUploadProgress.value = 0;
  syncSelection();
  syncRound();
  requestOpen.value = true;
}

const beforeISOUpload: UploadProps['beforeUpload'] = (file) => {
  const uploadFile = file as File;
  const validationMessage = validateVMISOFile(uploadFile);
  if (validationMessage) {
    message.warning(validationMessage);
    return false;
  }

  isoUploading.value = true;
  isoUploadProgress.value = 0;
  const controller = new AbortController();
  isoUploadController.value = controller;
  void uploadVMISOApi(uploadFile, {
    onProgress: (percent) => {
      isoUploadProgress.value = percent;
    },
    signal: controller.signal,
  })
    .then((stored) => {
      requestForm.imageUrl = resolveVMISOUrl(
        stored.url,
        window.location.origin,
      );
      message.success('ISO 上传完成');
    })
    .catch(() => undefined)
    .finally(() => {
      isoUploading.value = false;
      isoUploadController.value = undefined;
    });
  return false;
};

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (!isoUploading.value) return;
  event.preventDefault();
  event.returnValue = '';
}

onBeforeRouteLeave(() => {
  if (!isoUploading.value) return true;
  // oxlint-disable-next-line no-alert -- route guards require a synchronous choice.
  const shouldLeave = window.confirm(
    'ISO 正在上传，离开页面将中断上传。确认离开？',
  );
  if (shouldLeave) isoUploadController.value?.abort();
  return shouldLeave;
});

function disabledLeaseDate(current: Dayjs) {
  if (!current) return false;
  if (current.isBefore(dayjs().startOf('day'))) return true;
  if (isAdmin.value) return false;
  return current.isAfter(dayjs().add(14, 'day').endOf('day'));
}

function disabledRenewDate(current: Dayjs) {
  if (!current) return false;
  if (current.isBefore(dayjs().startOf('day'))) return true;
  return current.isAfter(dayjs().add(7, 'day').endOf('day'));
}

async function submitRequest() {
  const validationMessage = validateVMRequestForm(requestForm, isAdmin.value);
  if (validationMessage) {
    message.warning(validationMessage);
    return;
  }

  requestSubmitting.value = true;
  try {
    const payload = buildVMRequestPayload(requestForm, isAdmin.value);
    const specs: { arch: string; count: number }[] = [];
    if (
      requestForm.archSelections.includes('aarch64') &&
      requestForm.aarch64Count > 0
    ) {
      specs.push({ arch: 'aarch64', count: requestForm.aarch64Count });
    }
    if (
      requestForm.archSelections.includes('x86_64') &&
      requestForm.x86_64Count > 0
    ) {
      specs.push({ arch: 'x86_64', count: requestForm.x86_64Count });
    }
    const totalCount = specs.reduce((sum, s) => sum + s.count, 0);

    if (totalCount > 1) {
      await createVMBatchApi(
        { ...payload, specs },
        createIdempotencyKey('vm-batch'),
      );
      const parts = specs.map((s) => `${s.arch} ${s.count}`).join(' + ');
      message.success(`已提交 ${totalCount} 台 VM 申请（${parts}）`);
    } else {
      await createVMRequestApi(
        { ...payload, arch: specs[0]?.arch ?? '' },
        createIdempotencyKey('vm-request'),
      );
      message.success('VM 申请已提交，可在申请记录查看进度和日志');
    }
    resetIdempotencyAttempt(requestIdempotency);
    requestOpen.value = false;
    activeTab.value = 'requests';
    requestPage.value = 1;
    await loadData();
  } finally {
    requestSubmitting.value = false;
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

  renewSubmitting.value = true;
  try {
    const payload = {
      expected_ends_at: renewForm.expectedEndsAt.toISOString(),
    };
    await extendLeaseApi(
      renewTarget.value.current_lease_id,
      payload,
      idempotencyKeyFor(renewIdempotency, 'extend', payload),
    );
    resetIdempotencyAttempt(renewIdempotency);
    message.success('租约已续期');
    renewOpen.value = false;
    await loadData();
  } finally {
    renewSubmitting.value = false;
  }
}

async function loadCredentialsForDetail(record: ResourceRecord) {
  const requestToken = ++credentialRequestToken;
  credentials.value = null;
  credentialLoading.value = false;
  if (!canViewCredentials(record)) {
    return;
  }
  credentialLoading.value = true;
  try {
    const loadedCredentials = await getResourceCredentialsApi(record.id);
    if (
      requestToken === credentialRequestToken &&
      detailOpen.value &&
      selectedVM.value?.id === record.id
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

async function refreshVMIp(record: ResourceRecord) {
  refreshingIpId.value = record.id;
  try {
    const refreshed = await refreshVMIpApi(record.id);
    updateVMRecord(refreshed);
    message.success('OS IP 已刷新');
  } finally {
    refreshingIpId.value = null;
  }
}

function openDetail(record: ResourceRecord) {
  selectedVM.value = record;
  powerState.value = null;
  powerStateError.value = '';
  detailOpen.value = true;
  void loadCredentialsForDetail(record);
  void loadPowerState(record);
}

watch(detailOpen, (open) => {
  if (!open) {
    clearDetailCredentials();
    powerStateRequest.invalidate();
    powerLoading.value = false;
  }
});

watch(requestDetailOpen, (open) => {
  if (!open) {
    requestEventsRequest.invalidate();
    requestEventsLoading.value = false;
  }
});

async function openRequestedVM(resourceId: string) {
  showAll.value = true;
  const target = await getResourceApi(resourceId).catch(() => null);
  if (target?.resource_type === 'VIRTUAL') {
    openDetail(target);
  } else {
    message.warning('VM 不存在或已不可用');
  }
}

async function openConsole(record: ResourceRecord) {
  await router.push({
    name: 'VirtualMachineConsole',
    params: { resourceId: record.id },
    query: { tabTitle: vmConsoleTabTitle(record) },
  });
}

function openPasswordModal(record: ResourceRecord) {
  selectedVM.value = record;
  passwordForm.sshPassword = '';
  passwordOpen.value = true;
}

async function submitPassword() {
  if (!selectedVM.value) return;
  if (!passwordForm.sshPassword) {
    message.warning('请输入 SSH 密码');
    return;
  }

  passwordSubmitting.value = true;
  try {
    const updated = await updateResourceApi(selectedVM.value.id, {
      ssh_password: passwordForm.sshPassword,
    });
    updateVMRecord(updated);
    await loadCredentialsForDetail(updated);
    passwordOpen.value = false;
    message.success('SSH 密码已更新');
  } finally {
    passwordSubmitting.value = false;
  }
}

async function operatePower(action: VMPowerAction) {
  if (!selectedVM.value) return;
  powerActionLoading.value = action;
  powerStateError.value = '';
  try {
    const payload = { action };
    const result = await operateVMPowerApi(
      selectedVM.value.id,
      payload,
      idempotencyKeyFor(powerIdempotency, 'vm-power', {
        resourceId: selectedVM.value.id,
        ...payload,
      }),
    );
    resetIdempotencyAttempt(powerIdempotency);
    powerState.value = result.power_state;
    message.success(`VM ${powerActionLabel(action)}命令已发送`);
  } finally {
    powerActionLoading.value = null;
  }
}

function openRequestDetail(record: VMRequestRecord) {
  selectedRequest.value = record;
  requestEvents.value = [];
  requestDetailOpen.value = true;
  void loadRequestEvents(record.id);
}

async function jumpToVMFromRequest() {
  if (!selectedRequest.value?.resource_id) return;
  const resourceId = selectedRequest.value.resource_id;
  requestDetailOpen.value = false;
  await openRequestedVM(resourceId);
}

function releaseVM(record: ResourceRecord) {
  const payload = { reason: '用户释放 VM' };
  const idempotencyKey = idempotencyKeyFor(
    createIdempotencyAttempt(),
    'vm-release',
    { resourceId: record.id, ...payload },
  );
  Modal.confirm({
    content: `确认释放并销毁 ${displayValue(record.primary_ip || record.vm_name || record.name)}？`,
    okText: '释放',
    onOk: async () => {
      await releaseVMApi(record.id, payload, idempotencyKey);
      message.success('VM 释放任务已提交');
      detailOpen.value = false;
      await loadData();
    },
    title: '释放 VM',
  });
}

function batchReleaseVM() {
  const ids = selectedVmIds.value;
  if (ids.length === 0) return;
  Modal.confirm({
    content: `确认批量释放并销毁 ${ids.length} 台 VM？`,
    okText: '批量释放',
    onOk: async () => {
      const result = await batchReleaseVMApi(
        ids,
        { reason: '用户批量释放 VM' },
        createIdempotencyKey('vm-batch-release'),
      );
      const failed = result.failed?.length ?? 0;
      if (failed > 0) {
        message.warning(
          `已提交 ${result.destroyed.length} 台，${failed} 台无权或无租约跳过`,
        );
      } else {
        message.success(`已提交 ${result.destroyed.length} 台 VM 释放任务`);
      }
      selectedVmIds.value = [];
      await loadData();
    },
    title: '批量释放 VM',
  });
}

function cancelRequest(record: VMRequestRecord) {
  Modal.confirm({
    content: '确认取消这个 VM 申请？',
    okText: '取消申请',
    onOk: async () => {
      await cancelVMRequestApi(record.id);
      message.success('申请已取消');
      await loadData();
    },
    title: '取消 VM 申请',
  });
}

function changeVMPage(pagination: TablePaginationConfig) {
  vmPage.value = pagination.current ?? 1;
  void loadData();
}

function changeRequestPage(pagination: TablePaginationConfig) {
  requestPage.value = pagination.current ?? 1;
  void loadData();
}

function changeShowAll() {
  vmPage.value = 1;
  requestPage.value = 1;
  void loadData();
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    vmPage.value = 1;
    void loadData();
  }, 300);
}

function onSearchEnter() {
  if (searchTimer) clearTimeout(searchTimer);
  vmPage.value = 1;
  void loadData();
}

watch(
  () => requestForm.installType,
  (installType) => {
    requestForm.dist = '';
    requestForm.osVersion = '';
    requestForm.imageRound = '';
    requestForm.imageUrl = '';
    if (installType === 'auto') {
      syncSelection();
      syncRound();
    }
  },
);
watch(
  () => requestForm.dist,
  () => {
    if (requestForm.installType === 'manual') return;
    requestForm.osVersion = '';
    requestForm.imageRound = '';
    syncSelection();
    syncRound();
  },
);
watch(
  () => requestForm.osVersion,
  () => {
    if (requestForm.installType === 'manual') return;
    requestForm.imageRound = '';
    syncRound();
  },
);
watch(
  () =>
    [
      requestForm.osVersion,
      requestForm.imageRound,
      requestForm.archSelections.join(','),
    ] as const,
  () => {
    void loadKernelVariants();
  },
);
watch(
  () => route.query.vm_id,
  (resourceId) => {
    if (typeof resourceId === 'string') void openRequestedVM(resourceId);
  },
);

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload);
  const requestedResourceId =
    typeof route.query.vm_id === 'string' ? route.query.vm_id : null;
  if (requestedResourceId) showAll.value = true;
  // Open requested VM detail first — don't block on data loading.
  // If loadImages() throws, Promise.all would reject and openRequestedVM
  // would never be called, leaving the user with a loaded list but no drawer.
  if (requestedResourceId) {
    void openRequestedVM(requestedResourceId);
  }
  void Promise.all([loadImages(), loadData()]);
});

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload);
  isoUploadController.value?.abort();
});
</script>

